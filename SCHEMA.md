# Corpus schema v0 (0.18.0)

Three semantic layers: language-neutral Latin, per-language gloss/editorial
content, and a corpus-wide lexicon. Since 0.16.0 each Latin text is a neutral
core and each target language is an independently publishable, potentially
partial package. The lexicon likewise keeps neutral lemma data apart from each
language's senses. JSON, UTF-8.
`form` uses 1962
liturgical orthography (u/v, j for consonantal i, æ/œ, accents — see
ORTHOGRAPHY.md); `lemma` is dictionary-normalized (i-form, no j) for analyzer
matching. Normalization of forms (strip accents, æ→ae, j→i) is derived
mechanically, never stored.

## Translation provenance ledger

`languages/<lang>/translation-provenance.json` contains one entry for every
translated `verse segment` in that language's published text set. Its site set
must equal the language manifest exactly.
Each entry carries:

- `site`, `text`, `segment`, and `language` — the complete stable address;
- `familiar_core` — whether exact recognizability is being protected while the
  wording's history is established;
- `origin` — `working-unsettled`, `own`, `public-domain`, `traditional`, or
  `trivial`;
- `review` — `working`, `internally-reviewed`, or `expert-reviewed`;
- `source_sha256` and `target_sha256` — hashes binding the state to the Latin
  segment and target string actually reviewed.

`working-unsettled` is a working-edition provenance state, not a legal verdict.
An inherited origin requires a wording citation; `own` and `trivial` prohibit
one. `checks/translation_provenance.py` rejects missing, duplicated, orphaned,
or stale entries. A source or target change therefore makes review provenance
stale rather than silently inheriting it.

`languages/<lang>/translation-basis.json` groups inherited sites by text and,
where necessary, segment. Its `relationship` says how the published wording
relates to the cited historical witness: `exact`, `normalized`, `revised`, or
`traditional-composite`. The grouping keeps this reader-facing distinction
authoritative without repeating it in every translated segment. The reader
edition expands it only into the lazily loaded language artifact for the text.

Since 0.5.0 `schema_version` is corpus-wide: every text and lexicon document
carries the same number.

## File layout

```
texts/<category>/<name>.json          language-neutral Latin core
lexicon/lemmata.json                  language-neutral lemma data
languages/<lang>/manifest.json        coverage, localized titles and aliases
languages/<lang>/texts/<category>/<name>.json
                                      one target-language text layer
languages/<lang>/lexicon.json         senses for the language package
languages/<lang>/translation-provenance.json
                                      public states for that language's sites
languages/<lang>/translation-basis.json
                                      grouped relation to wording witnesses
```

The manifest is the authority for coverage. A language may publish any ordered
subset of the neutral texts, but each listed text is complete: every word has a
gloss, every verse a translation, every rubric a narrative, and every neutral
localization requirement is fulfilled. Missing languages never fall back to
another language silently.

The optional manifest `titles` object is keyed by covered text id. Each entry
has a nonempty `title` and may carry unique nonempty `aliases`. These are
reader search and display metadata, not alternate recensions. The reader
edition emits them beside each text's path and emits a manifest-named
`concordance.json` inside the language package. Search normalization is
case-insensitive, removes diacritics, expands æ/œ, and treats Polish ł as l;
display strings retain their authored, devotional capitalization.

Working analysis defaults, source pointers, notes and per-token analysis live
under the neutral document's `editorial` block. Its `localization` block records
language-independent topology: whether an introduction is required, which
words require contextual explanations or disputed-reading notes, and the shared
citations supporting introductions, explanations and rubric narratives. Citations
supporting the particular wording of a translation remain in its language
package. `build_reader/store.py` combines these layers only in memory for checks.

## The three layers of word help (binding division of labor)

Every fact lives in exactly one layer; a reader-facing sentence must not
restate what another layer already carries:

1. **Lexicon** (per lemma, written once): dictionary head, part of speech,
   paradigm data, senses, lemma-level notes (etymology, usage). True of the
   word everywhere.
2. **Morphology** (per token, structured): the `morph` object states THE
   parse in this context — apps render it as prose. This is where formal
   ambiguity (María vocative, not nominative) is resolved.
3. **`explanation`** (per token, prose, OPTIONAL): a reader-facing insight
   true of this occurrence and not derivable from the other two layers —
   meaning, imagery, idiom, ellipsis, a translation difficulty, textual
   history, or a liturgical and scriptural resonance. It is not a prose
   rendering of the parse; see the language-layer section.

## Word IDs (binding rules)

- Global per text, zero-padded to a minimum of three digits: `w001`…`w999`,
  then `w1000` and beyond without a maximum width. Referenced externally as
  `<text-id>.<word-id>` (e.g. `ordinarium.confiteor.w002`) by SRS decks and
  future GABC syllable maps (`w002.s1` reserved for syllables).
- **Never renumbered, never reused.** Document order = array order, not ID
  order. IDs are opaque stable tokens: the numeric appearance is allocation
  history, not position. A textual insertion takes the NEXT FREE NUMBER in
  its text, wherever it lands in reading order — the array carries the
  order, the ID carries only identity.
- Segment IDs (`s01`…) are stable identities under the same discipline as
  word IDs: the reader publishes them in shareable verse addresses
  (`?s=s02-s04`), so once a segment id has existed it is live or retired,
  forever, and never renamed or reused. Their two-digit padding is a
  minimum, not a limit: `s99` is followed by `s100`. Document order always
  comes from the segment array, never from lexicographic ID sorting.
  Segmentation may still improve — a split keeps the surviving id on the
  segment that keeps (some of) its words and mints new ids for the rest; a
  merge or removal retires the vanished id to the surviving segment that
  now carries its content.
- **The mint is recorded, not inferred.** Every text carries
  `"ids": {"next": N}`, and a new word takes `next` and moves it on. Inferring
  the next free number as one past the highest works only until a word is
  removed, and a corpus that has never removed one is a corpus whose rule has
  never been tested. Segments carry their own recorded mint the same way:
  `"ids": {"segments": {"next": M}}`, and a new segment takes `M`.
- **A removed word leaves a tombstone**: `"ids": {"retired": {"w042": "s03"}}`,
  naming the nearest segment that survives it. A deep link to a retired word
  resolves to that segment rather than dangling. Ids are never reused, so a
  tombstone is permanent.
- **A removed segment leaves a retirement record**:
  `"ids": {"segments": {"retired": {"s07": "s05"}}}`, naming the live
  segment that now carries its content. The reader edition ships the map
  (`rs` on the text artifact), so the app resolves a retired `?s=` address
  to the surviving verse and canonicalizes the link. Retirement records are
  permanent, and a retired id never returns to life. Identifiers from
  before this contract (the 2026 `ave1`–`ave3` aliases) appear as
  retirement keys in their historical shape, so the oldest published
  addresses still resolve.
- `checks/identity.py` enforces all of the above, and compares against git —
  the base branch in CI, HEAD locally — because "was this id reassigned" is a
  question about history that no single snapshot can answer. A renumbering
  cannot merge.

## Latin source layer

```
schema_version, id, title, category, section, variant, sung, segments[],
localization, editorial
```

- `status`: `"working-edition"` until expert review (quality rule).
- `source` (since 0.3.0): provenance — how the text entered the corpus,
  pointer to its `witnesses/<text-id>/` directory and `apparatus.json`
  (adjudicated accidental variants). Collation (checks/collate.py)
  enforces zero substantive divergence from every witness. The apparatus
  pointer is bidirectional: if the file exists, `source.apparatus` must name
  it and the file's `text` must name the document; a pointer to no file is
  also an error.
- An apparatus carries a derived `summary` beside its prose `note`:
  `entries` is the length of `adjudicated`, and `classes` is the sorted set
  of classes those entries use. `python -m checks.apparatus --write`
  regenerates every summary; the corpus gate rejects a stale one. Arithmetic
  and class membership therefore never depend on copied prose.
- A witness header may identify one or more archived source spans in its
  `path` value, using `line N` or `lines N-M`; wrapped values and two-file
  declarations are read in full. Once a header claims source lines, syntax
  the verifier cannot parse fails closed. Only a witness with no line
  declaration at all may use the deliberate whole-archive fallback.
- Every witness with such a declaration and a matching local raw archive is
  also checked as a transcription. The check preserves letters, accents,
  capitalization, ligatures, and comma placement while removing only declared
  source framing (speaker markers, rubrics, runtime calls, and name slots).
  Composed witnesses are checked clause by clause against the ordered union of
  their named spans. A declared raw path with no local archive is an error.
- **`head`** and **`substantive`** (since 0.13.0) state the SYNTAX, which is
  the one thing that settles a reading the form permits and the sentence
  forbids. Every adjective, numeral and
  participle carries either `head`, the id of the word it must agree with, or
  `substantive: true`, meaning it agrees with nothing expressed — it heads its
  own phrase (*Salus infirmórum*, the health of the sick) or is impersonal
  (*postquam cenátum est*). Every preposition carries a `head` naming the word
  it governs. `checks/syntax.py` then verifies on every build that a modifier
  matches its head in case, number and gender, that a preposition's object
  stands in a case that preposition governs, and that a predicate complement or
  a nominative relative matches its verb in number.
  Three rules keep the claim honest. A head may stand in ANOTHER SEGMENT: a
  segment is a unit of layout, not of syntax, and the Canon's sentences run
  across four and five of them. A PERSONAL PRONOUN lends no gender — the corpus
  records none for *nos*, *tu*, *mihi* — so an adjective agreeing with one
  (*omnes nos*, *benedícta tu*) is checked on case and number alone. A
  PARTICIPLE used substantively is a nominal and takes agreement like one
  (*ómnium circumstántium*); only a FINITE verb head means "agrees with the
  subject of this verb", where number is the only feature a verb can settle.
  `substantive` is data and not a default, because "this adjective is really a
  noun" is the assumption that buried 131 real agreement failures in noise when
  the check was first attempted without heads. The verdict line reports
  `syntax=declared/total`, which reached 1289/1289 on 2026-08-16. The annotation
  is COMPLETE, so a modifier that declares neither a head nor `substantive` now
  FAILS the build: a new word entering the corpus must say what it modifies, or
  say that it modifies nothing.
  Two rules constrain the SHAPE of the head graph, not the features, because
  agreement is symmetric and cannot police itself: two coordinate modifiers
  agree with each other by construction (*dignum et iustum*, *ómnibus Sanctis*),
  so a pair naming each other satisfies every feature test while recording
  nothing. A head that names a word which names it back is an ERROR, and so is a
  modifier whose head is itself a dependent modifier — name that modifier's own
  head instead. A head may still stand in another SEGMENT, but it must stand in
  the same SENTENCE: 165 heads had reached past a full stop to the first word
  that happened to agree.
- `analysis_defaults`: the `analysis` object assumed for every word/segment
  that does not carry its own (`confidence`: high|medium|low, `sources`:
  [whitakers|collatinus|editorial|treebank|expert|<witness-id>], `review`:
  pending|accepted|disputed). Witness ids (e.g. `do`, `handmissal-eo`) are
  valid sources for rubric/text-level claims.
- `analysis_defaults_words` (since 0.7.0, optional): the default for WORD
  tokens specifically. Resolution order: `word.analysis` ??
  `analysis_defaults_words` ?? `analysis_defaults`; segments never read it.
  Rationale: word analyses are machine-confirmed by independent analyzers
  (the agreement report names each token's confirmers), while segment-level
  prose claims remain editorial — one document-wide default could not say
  both. A per-word `analysis` appears ONLY where the confirmers differ from
  the word default (e.g. proper names absent from one analyzer's lexicon);
  an override that restates its default is a lint error, as is a
  `analysis_defaults_words` identical to `analysis_defaults`.
- Segment: `{ id, type: "verse"|"rubric", verse?, speaker?, voice?, delivery?,
  text? (rubric Latin), words?[] }`. **`speaker`** (since 0.9.0) is who says it —
  `sacerdos`, `ductor`, `minister`, `populus`, `omnes`, `schola` — and **`voice`**
  is how loudly: `clara` (aloud), `submissa` (raised but not full, the
  *elata aliquantulum voce* of Dómine non sum dignus), `secreto`
  (silently), `cantus` (sung). Both belong to verse segments only: a
  rubric is the edition's framing, not anyone's words.
  `checks/attribute.py` PROPOSES both from the sources — the speaker from the
  witnesses' markers, aligned to the text in order — and it is run by hand,
  not by the build. What it proposes is written into the files and reviewed
  there, so these two fields are AUTHORED with a tool's help rather than
  derived on every run, which `participation` is and they are not. Until
  2026-08-19 this paragraph said they were "READ from the sources … never
  remembered", and an external review found the propers' values hand-written,
  the module ignorant of the `schola` and `cantus` the propers use, and
  `run_checks` never calling it. The speaker is read from the witnesses' markers — which come
  in both cases, the Ordo printing the priest's own Confiteor as a
  lowercase `v.` — aligned to the text IN ORDER, because a dialogue that
  repeats itself (the Kyrie's nine invocations of two phrases) cannot be
  read by content alone. Where a passage of the Mass carries no marker at
  all, the speaker is the celebrant: the Ordo marks every other voice, and
  the Ritus servandus names sacerdos as the actor throughout. Outside the
  Mass no such reasoning holds. A devotional dialogue may use `ductor` for
  the person leading it: unlike `sacerdos`, this does not imply ordination,
  and is therefore suitable for a family or other lay group. A devotional
  prayer takes no clerical attribution from a bare V. marker.
  `verse` is an optional positive integer for a segment whose conventional
  biblical verse number is known. It belongs to the corpus, not to an app-side
  slug table, and must be unique within the text.
  Since 2026-08-06 the voice comes chiefly from the rite's own
  law — **Rubricae generales IX, n. 511**, which lists what is said clara
  voce at low Mass and closes *"Cetera dicuntur secreto"*, transcribed in
  `witnesses/raw/mr-rubricae-generales-ix.txt`. That is what the rubrics
  inside the texts could not give: the Canon's silence is stated once, in
  the law (n. 500), and never repeated on the page. Where a text's own
  rubric disagrees with the law the tool REPORTS it rather than choosing
  quietly; n. 512 defines the terms, `secreto` being said "ut ipsemet se
  audiat, et a circumstantibus non audiatur". — the speaker from the witnesses' own markers (S. sacerdos,
  M. minister, V./R. a versicle and its response, O. omnes), which the
  transcriptions strip and every witness header says so; the voice from
  the rubrics this corpus already carries. Both are OPTIONAL, and their
  absence is meaningful: it says the sources have not been read for this
  segment yet, which the reader's app must render as unmarked rather than
  guess. `run_checks` reports the coverage as `speakers=N/M`.
  **`delivery`** (since 0.15.0) records a form-specific exception to those
  base values: `{ lecta?: {speaker?, voice?}, cantu?: {speaker?, voice?} }`.
  It exists because the Proper is read aloud by the celebrant at low Mass but
  its chants are delivered by the schola at sung Mass. The base `speaker` and
  `voice` remain the low-Mass reading (`sacerdos`, `clara`); a Proper chant
  carries `delivery.cantu: {speaker: "schola", voice: "cantus"}`. Consumers
  select the requested form and overlay only the named fields. Empty,
  redundant, unknown, or rubric-level overrides are errors. This layer is
  DERIVED by `checks/delivery.py`, not authored separately in each formulary.
- Segment: **`participation`** (since 0.10.0) is who among the FAITHFUL makes
  this line, and on whose authority. `speaker` answers a different question —
  whom the Missale charges with the line — and at low Mass the answer is
  always the minister, which is true and is not what a person in the pew
  needs. The two must not be conflated: an edition that prints *ministrant*
  over the line a congregation is about to say has answered the wrong
  question.
  Shape: `{ lecta?: {gradus?, source, conditional?}, cantu?: {gradus?, source,
  conditional?} }`. The two
  keys are the two forms of Mass the law grades separately — `lecta` the low
  Mass, `cantu` the sung Mass — because they are not the same event, and a
  reader at a sung Sunday Mass has more of the Ordinary than one at a said
  Mass. `gradus` is the degree of participation, 1 to 4; it is ABSENT where
  the law grants a part without grading it (n. 32, the Pater noster).
  `conditional: true` distinguishes a faculty dependent on the faithful's
  preparation or a selected trained group from an unconditional congregational
  answer. False is never stored. A reader must present this as “may join”, not
  mark the line as though it belonged unconditionally to the congregation.
  The source is the Instruction **De musica sacra et sacra liturgia** (Sacra
  Rituum Congregatio, 3 September 1958), nn. 25-26 and 31-32, transcribed in
  `witnesses/raw/scr-de-musica-sacra-1958.txt`; n. 26 extends the sung-Mass
  degrees verbatim to the Missa cantata, which is the form a parish keeps on
  Sundays.
  DERIVED, never remembered: `checks/participation.py` computes every
  attribution from the text a segment prints and the speaker its witnesses
  gave it, and `run_checks` fails if a file carries anything else. The
  speaker is part of that test and not a formality — the corpus holds eight
  segments reading *Amen* and three are the priest's, one of them said
  secreto, so a rule reading n. 31 a as a list of strings would hand the
  people a line the priest says silently.
  Absence is meaningful here too: the instruction legislates for the Mass, so
  the devotional prayers this corpus carries — the Leonine prayers, the
  Marian antiphons — take nothing from it. `run_checks` reports the coverage
  as `participation=N`.
- Word: `{ id, form, post?, lemma, morph, analysis? }`. `post` = trailing
  punctuation rendered after the word (`,` `;` `:` `.` `?`). `degree`
  (`comp`/`sup`) is not confined to adjectives: Latin adverbs take it too
  (*mirabílius*), and the analyzers report it. `lemma` is the key
  into `lexicon/lemmata.json` — dictionary-normalized (i-form,
  no j, full head: `ab` not `a`) and **lowercase except true proper names**
  (Maria, Michael, Ioannes, Petrus, Paulus, Iesus, Christus, Abel, Abraham,
  Melchisedech, the saints of the Canon's two lists… — `PROPER_LEMMAS` in
  `checks/lint.py` is the list, and grows as texts require); divine titles
  (deus, dominus, pater, spiritus) are lowercase common-noun lemmas. (0.4.0 removed the 0.2.0
  `tier` field: hand-judged per-word difficulty proved unreviewable.)
- `morph`: `pos` (verb|noun|adj|pron|adv|conj|prep|intj) plus per-pos fields —
  nouns/adjs/prons: `case` (nom|gen|dat|acc|abl|voc), `number` (sg|pl),
  `gender` (m|f|n), nouns also `decl` (1–5, omitted for Greek/irregular
  declensions such as Iesus); adjs: `degree` (comp|sup) when not positive;
  verbs: `person`, `number`, `tense` (pres|impf|fut|perf|plup|futperf),
  `mood` (ind|subj|imp|inf|part), `voice` (act|pass|dep), `conj` (1–4,
  omitted for irregulars such as sum, fio); preps: `governs` (acc|abl);
  intj covers indeclinables like Amen. **Participles** (since 0.8.0) are
  verb tokens with `mood: "part"`: no `person`, and they add the nominal
  agreement fields `case`/`number`/`gender` to `tense` (pres|perf|fut)
  and `voice` (deponent participles keep `voice: "dep"`, present as well as perfect).
  Extend enums as texts require (gerundives are not yet covered).
  Classification rulings: *sicut* is tagged `conj`
  (comparative conjunction) although several dictionaries head it as an
  adverb — analyzer disagreement at integration is expected there, not a
  silent error.

### Homograph lemma keys

Two different words can share a spelling: the demonstrative *hic, hæc, hoc*
and the adverb *hic* ("here"). The lexicon is keyed by lemma with one part of
speech per entry, so they cannot share a key.

The plain key goes to the word a reader is likelier to look up — usually the
more frequent one — and the other takes a discriminator, `<lemma>_<latin
part of speech>`: `hic` is the demonstrative, `hic_adverbium` the adverb.
Letters and underscore only: a hyphen breaks the analyzer lookup, which
expects a single Latin word. The pipeline maps a discriminated key back to
the word itself (`LEMMA_ALIASES`), so the analyzers still vote on it, and the
app strips the discriminator when it builds an external dictionary link.

### The gerundive

A gerundive is the future passive participle, and is written as one:
`mood: part`, `tense: fut`, `voice: pass`, plus the case, number and gender
of its agreement. No enum value is invented for it, and none is needed — the
analyzers describe it the same way. That it carries obligation ("to be
offered", "which must be offered") is a matter of sense and belongs in the
word's note, not in the morphology.

The gerund — the verbal noun, active in sense and without agreement — is
NOT this. When one is tokenized, it wants its own ruling.

### `sung`

`sung: true` marks a text that the CHANT BOOKS set: the five chants of
the Kyriale ordinary (Kyrie, Gloria, Credo, Sanctus, Agnus Dei), the
preface with its dialogue, and the dismissal, which the Kyriale prints
with a melody for each Mass setting. It is a fact about the books, not
about a particular celebration — every one of these is spoken at a low
Mass, and much else is sung at a solemn one. The chant policy (v1 carries
the texts, not the notation) is what this field serves: it says which
texts a reader will meet as music.

### Apparatus classes

Every entry in a text's `apparatus.json` carries a `class`, and the class
decides where the collation will accept it. Two of them settle differences
in the LETTERS, and both need a ruling that quotes both readings:

- **`orthography`** — a different real spelling of the same word:
  neglegentia against negligentia, genetrix against genitrix, and the
  i-for-j of ORTHOGRAPHY.md. Both are the word, neither page is wrong.
  Reported as `orthographic=N`.
- **`inflection`** (since 2026-08-07) — a name this edition leaves
  indeclinable and the witness declines. Latin took the Hebrew names in
  twice: *Ioseph* never changes, *Iosephus* declines, so one page sets
  *cum beato Ioseph* and another *cum beato Iosepho*. The letters differ
  because the grammar does, which is a question about the text and not
  about spelling — so it is counted apart, as `inflections=N`, and the
  token is normally marked `review: disputed` as well, to reach the list
  an expert reads.
- **`omission`** — a full witness lacks a word printed by this edition and
  another full witness. Its witness reading is the empty string. The ruling
  identifies the positive evidence for retaining the word. Reported as
  `omissions=N`. An omission cannot be inferred from a partial witness.

The remaining classes settle ACCIDENTALS — punctuation, capitalization,
and accents — and are compared only against a witness that has not
declared `profile: substantive-only`. `capital-accent` is generated by
`checks/house_rules` and may be used ONLY where the accent that differs
sits on a capital; a page that drops accents from lowercase words drops
them altogether, which is a fact about the page, declared once by its
profile, and not something to assert word by word.

**A ruling that matches nothing the named witness prints is an error.**
It is a claim about a page, recorded in a public apparatus, that the page
does not support.

The class applies to each named witness reading, not merely to the token.
If two witnesses differ at the same token for different reasons, write two
entries with disjoint `witnesses` maps. For example, *Joseph* against
*Ioseph* is orthography, while *Iosepho* against indeclinable *Ioseph* is
inflection; combining both readings under either label is refused.

### Witness corrigenda

A witness may set a letter wrong — a printer's slip, not a reading. That is
neither an adjudicated variant nor something to pass over, so the witness
file declares it in its header:

```
# corrigendum: princípo -> princípio (this printing drops the i; the same
#   edition sets the doxology correctly on printed page 11)
```

The transcription then carries **what the page prints**. Collation applies
declared corrigenda before comparing, refuses a declaration whose printed
reading is not in the file, refuses one without a reason, and reports the
count (`corrigenda=N`) in the verdict. A corrigendum is a claim about a
page, so it names the evidence for the emendation, as an apparatus ruling
does.

### Witness recension notes

A witness may instead be **right about a different text**. The same prayer
circulates in more than one recension: a page giving the devotional form
of an antiphon closes it with an Amen where the liturgical form runs
straight on to its versicle. Nothing is wrong with the page, and nothing
is wrong with the edition — they attest different forms — so the witness
file declares the difference and the transcription still carries **what
the page prints**:

```
# recension: -Amen (after "Virgo Maria"; this page gives the devotional
#   form, which closes the antiphon with an Amen; the Leonine recension
#   has none and witness do runs on to the versicle)
```

Only the minus direction exists. Dropping a word the witness has is a
claim about the witness; adding one it lacks would be a claim about our
own text that no page attests, and a word this edition prints must stand
in a witness. Collation applies declared removals before comparing, and
refuses a note that names a word the page does not print, one that names
a word this edition prints too (that is a divergence to adjudicate, not a
recension difference), or one without a reason. Reported as
`recensions=N` in the verdict.

## Lexicon

`lexicon/lemmata.json` (language-neutral):

```
schema_version, status, analysis_defaults,
entries{ <lemma>: { head, pos, gender?, gender_pl?, decl?, conj?, analysis? } }
```

- Keys are the normalized `lemma` strings used by the text documents —
  coverage is checked both ways: every text lemma has an entry, every entry
  is used by at least one text.
- `head`: the reader-facing dictionary head in **1962 liturgical orthography
  with accents** (ORTHOGRAPHY.md applies to every component) — the lemma key
  is bare and normalized, the head is what a reader sees (`Ioánnes` for the
  lemma `Ioannes`, `maiéstas, maiestátis` for `maiestas`).
  Conventions: nouns give the genitive (`mater, matris`; it may be
  abbreviated to its ending for the 1st, 2nd and 4th declensions —
  `culpa, -æ`, `dóminus, -i`, `spíritus, -us` — except that nouns in
  -ius/-ium print the genitive in full, `solácium, solácii`, because `-i`
  after such a stem reads as a genitive in `-i` and the running text
  prints `-ii`); adjectives give the feminine/neuter
  endings (`beátus, -a, -um`; one-ending adjectives the genitive:
  `omnípotens, omnipoténtis`); verbs give principal parts
  (`oro, oráre, orávi, orátum`; deponents `precor, precári, precátus sum`);
  indeclinables just the word. No gender marker inside `head` — gender is
  structured, apps render it.
- `pos` and the paradigm fields reuse the morph enums: nouns carry `gender`
  and `decl` (omitted for Greek/irregular declensions such as Iesus), verbs
  carry `conj` (omitted for irregulars such as sum, fio). These are
  auto-compared against every token's morph — the lemma layer and the token
  layer must never disagree silently.
- `gender_pl`: dictionary gender of the plural where it differs (heteroclite
  cælum: `gender: "n"`, `gender_pl: "m"`) — keeps the consistency check
  strict instead of exempting the word.
- `gender_alt` (since 0.8.0): a second dictionary gender where the word
  genuinely carries both (dies: `gender: "m"`, `gender_alt: "f"` for
  appointed days — tértia die). A token may use either; the consistency
  check accepts both and nothing else.

`languages/<lang>/lexicon.json` (one per published language):

```
schema_version, language,
entries{ <lemma>: { senses[], note?, derivatives?, analysis? } }
```

- `senses`: 1–4 short dictionary-style meanings in the target language,
  ordered by relevance to liturgical usage. Our own editorial wording —
  NEVER copied from protected dictionaries.
- `note`: optional lemma-level remark (etymology, register, usage) — facts
  true of the word everywhere. What used to be repeated on every token of
  `amen` lives here now. A lemma page supplies no verse or prayer as an
  antecedent, so deictic wording such as “w tym wersecie” / “in this verse”
  is forbidden. Move that claim to the occurrence's `explanation`, or name an
  indispensable context explicitly (“In Psalm 118:34…”).
- `note_citations` (since 0.11.0): optional reader-facing sources for the
  localized `note`. Since 0.16.0 the note requirement and citations live once
  under the neutral lemma's `localization` field.
- `derivatives` (since 0.6.0): optional, 1–6 words of the TARGET language
  genuinely derived from or borrowed via this lemma (confíteor →
  konfesjonał; panis → companion) — memory hooks for learners. Only real
  descent counts; lookalikes and independent cognates do not (mors is NOT
  the source of Polish "mord"). A word that descends through the lemma's
  base or a sibling of the same root family, rather than through the
  lemma itself, names its true ancestor in parentheses: „kustosz (od
  custos)”, "custody (from custódia)". Per-language by nature: no parity
  requirement, and entries differ freely between languages.
- A language lexicon must cover every lemma reachable from the texts in that
  language's manifest. It may grow ahead of published text coverage, but may
  not contain a lemma unknown to the neutral lexicon.

## Language layer

```
schema_version, language, text, about,
segments{ <seg-id>: { translation, translation_citations? | narrative } },
words{ <word-id>: { gloss, explanation?, note? } }
```

- `about` (since 0.8.0; required for a published text): one short paragraph introducing the
  text — history, when it is prayed, structure — in the target language.
  Reader-facing and collapsed by default in apps; every claim must be
  true and verifiable (the quality doctrine applies as to any layer).
  Its presence is declared by the neutral core, not inferred from another
  target language.
- `about_citations` (since 0.11.0): optional reader-facing sources supporting
  the introduction. Since 0.16.0 these are written once in the neutral core.
- `gloss` (required): shortest natural reading aid in the target language
  (interlinear line). It may be idiomatic rather than grammatical — it is
  the sense the context selects, which no lemma-level sense list can supply.
  A token whose sense a neighboring word's gloss has absorbed (the
  auxiliary of a periphrastic whose participle glosses the whole tense)
  glosses as an em dash `—`: the declared interlinear null.
- `explanation` (OPTIONAL, contextual-only): usually 1–3 sentences that add a
  coherent reader-facing insight in the target language. Belongs here:
  meaning that a short gloss cannot carry, sacred imagery or referents,
  idiom and ellipsis, a consequential ambiguity and its adopted reading,
  a non-obvious translation difference, textual history, or scriptural and
  liturgical resonance. Does NOT belong here: agreement, government, case,
  person, number, or another bare parse restatement already rendered from
  `morph` and `head`; nor a lemma-level fact already in the lexicon. A formal
  term may appear when it is necessary to explain a genuine ambiguity, but
  it must serve the meaning rather than become the explanation's subject.
  Omit the key entirely when the gloss, form row, and lexicon already say
  everything. Required sites are declared by `localization.explanations` in
  the neutral core.
  **Self-contained prose** — each entry is read
  in isolation. The only permitted cross-reference is the quoted-form
  pattern `„form” (wNNN)` (EN: `“form” (wNNN)`): the app renders the quoted
  form as a tap-link to that word and hides the id; bare ids in prose are
  lint errors.
- `explanation_citations` (renamed in 0.17.0): optional reader-facing sources
  for the `explanation`. They are stored once at the corresponding
  `localization.explanations` site in the neutral core.
- `narrative` (rubric segments): "what is happening at the altar" in the
  target language.
- `narrative_citations` (since 0.11.0): optional reader-facing sources for
  the `narrative`, stored once in the neutral core since 0.16.0.
- `translation` (verse segments): our own working translation — NEVER copied
  from protected literary translations.
- `translation_citations` (since 0.12.0): optional sources that identify a
  public-domain or otherwise authorised rendering used as the basis of this
  target-language translation. They belong to the translation, may not exist
  without it, and are intentionally language-specific. A citation declares a
  basis or inheritance; it does not assert word-for-word identity unless the
  surrounding editorial record says so.
  `checks/rights.py` counts each translated segment-language site exactly once:
  a translation without this field is `own`; a site citing only public-domain
  wording is `public-domain`; a site with several sources takes the most
  restrictive recorded status. Deleting the field therefore changes the site
  to `own` rather than making it disappear from the report.

### Reader-facing citations

A citation supports the smallest prose unit that makes the claim. It is not
a detached bibliography and must not be used to restore history or commentary
that the prose itself does not need:

```json
{
  "title": "Catechismus Catholicae Ecclesiae",
  "locator": "n. 1449",
  "url": "https://www.vatican.va/..."
}
```

`title` names the work and `locator` gives the exact passage; both are
required nonempty strings. `url` is optional and, when present, must be an
absolute HTTPS address. Language-independent citation metadata is stored once
in the neutral core because the supported claim concerns the Latin text, not
its Polish or English wording. Elementary grammar and statements directly
visible in the displayed Latin do not receive decorative citations.
