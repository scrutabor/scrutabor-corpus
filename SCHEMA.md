# Corpus schema v0 (0.21.0)

Three semantic layers: language-neutral Latin, per-language gloss/editorial
content, and a corpus-wide lexicon. Since 0.16.0 each Latin text is a neutral
core and each target language is an independently publishable, potentially
partial package. The lexicon likewise keeps neutral lemma data apart from each
language's senses. JSON, UTF-8.
`form` uses 1962
liturgical orthography (u/v, i for consonantal i, æ/œ, accents — see
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
An `exact` or `normalized` site says that a page prints its wording, so at least
one retained use in the language's bibliography must name a page as the
`historical_wording_basis` of the site or its text. A comparator cannot carry
that claim.

Since 0.5.0 `schema_version` is corpus-wide: every text and lexicon document
carries the same number.

## File layout

```
texts/<category>/<name>.json          language-neutral Latin core
formularies/<collection>/<id>.json   ordered Mass assembly and calendar address
lexicon/lemmata.json                  language-neutral lemma data
languages/<lang>/manifest.json        coverage, localized titles and aliases
languages/<lang>/texts/<category>/<name>.json
                                      one target-language text layer
languages/<lang>/formularies/<collection>/<id>.json
                                      localized formulary title
languages/<lang>/lexicon.json         senses for the language package
languages/<lang>/translation-provenance.json
                                      public states for that language's sites
languages/<lang>/translation-basis.json
                                      grouped relation to wording witnesses
bibliography/graph.json               neutral evidence graph and parity state
languages/<lang>/bibliography.json    wording uses for one language only
```

The manifest is the authority for coverage. A language may publish any ordered
subset of the neutral texts, but each listed text is complete: every word has
exactly one direct gloss or one explicit alignment realization, every verse a
translation, every rubric a narrative, and every neutral
localization requirement is fulfilled. Missing languages never fall back to
another language silently.

## Mass formulary assemblies

`formularies/<collection>/<id>.json` is the canonical assembly contract for
one Mass. It keeps liturgical structure out of filenames and out of reader
applications. The stable `id` addresses the particular Mass; `observance`
groups variants of one day, while `calendar.key` addresses the computed Roman
calendar. These identities may deliberately differ. `calendar.default` marks
the single variant opened for a calendar occurrence. The unique integer
`order` is the canonical display and campaign order; consumers never recreate
that sequence from filenames or a private table.

The ordered `components` array names each unique component `key` and liturgical `role`,
the stable dotted text id, and its relationship to this assembly:

- `proper` is a text authored for this formulary;
- `shared` is a non-Proper text such as a common preface;
- `reference` explicitly transfers a Proper text from another formulary.

Transferred parts are never inferred from a missing filename. Every Proper
text must be reached by at least one assembly, every target must exist, and
component order follows the order of Mass. A multi-Mass observance gives every
member a distinct `variant` and exactly one calendar default.

Formulary schema `1.2.0` permits only these component conditions:

- `{"weekday": "sunday"}` or `{"weekday": "not-sunday"}` for the printed
  weekday distinction, such as the Christmas Vigil's preface (MR1962 p. 16);
- `{"season": "paschale"}` or `{"season": "not-paschale"}` for a printed
  Paschal alternative, such as the Annunciation chants (MR1962 p. 496);
- `{"season": "post-septuagesimam"}` or `{"season": "not-post-septuagesimam"}`
  for a printed "post Septuagesimam" alternative on a feast whose date falls
  on either side of Septuagesima Sunday, such as the Purification's tract
  (MR1962 p. 467). The branch covers the seasons `septuagesima`,
  `quadragesima` and `passionis`;
- `{"use": "votive-after-septuagesima"}` for source alternatives expressly
  limited to votive Masses after Septuagesima and before Easter, and
  `{"use": "votive-before-septuagesima-or-after-pentecost"}` for those limited
  to votive Masses before Septuagesima or after Pentecost, such as the Chair
  of Peter's Alleluia (MR1962 p. 478). These remain study material and are
  never selected by the calendar-only Ordo. This does not declare a complete
  votive formulary or permission to celebrate it.

No combined predicates, additional fields, arbitrary season lists, or implicit
defaults are allowed. The **actual calendar occurrence's** season governs the
Paschal branch, not the catalogue grouping or civil month. Missing or unknown
date/season context must not select either seasonal branch. An explicitly
undated study view retains and labels alternatives without presenting them as
one consecutive Mass. Repeated roles require exactly one of the complementary
weekday or season pairs and distinct stable keys.

Where the source changes words within a chant, publish separately reviewed
complete text recensions rather than hide words or manufacture acclamations in
the reader. A proper component may declare `recension: "paschale"` or
`recension: "non-paschale"`, with the matching season condition. The equivalent
Latin labels `tempore-paschali` and `extra-tempus-paschale` also bind to those
same two conditions. Its text id is
`proprium.<text_prefix>-<recension>-<role>`. The base recension retains its
original text id. Every recension has its own stable words, complete Latin and
target-language layers, source evidence, and translation provenance.

Each language package mirrors the neutral path with a small document carrying
the same formulary id, language id and localized title. The reader edition
publishes the neutral catalogue as manifest-declared `formularies.json` and
each localized title catalogue as `languages/<lang>/formularies.json`. Reader
text addresses use slash form (`proprium/<id>`) while authored documents retain
dotted corpus ids.

The manifest-declared `metrics.json` is derived from the same corpus snapshot.
It is the shared denominator for text, word, verse-segment, language-package,
formulary, observance and component-use counts; consumers do not maintain
independent copies of those totals.

## Bibliography and evidence graph

The bibliography is an identity graph rather than a list keyed by display
title. Its schema version is independent of the text schema. The neutral graph
contains:

- `works`: abstract works, with stable ids, responsible bodies/authors and
  uniform titles;
- `editions`: concrete editions, their recension, imprint, authority class and
  rights record. Every edition declares a sorted `languages` array. Reader-
  facing editions may use only Polish (`pl`), English (`en`) or Latin (`la`),
  so an unsupported modern-language layer cannot enter the public catalogue by
  accident;
- `digital_items`: individual scans or born-digital manifestations, each tied
  to one edition and a stable record or documented owner-held copy;
- `uses`: exact claims at typed text, segment, word or lemma addresses, with a
  role, decision, manifestation, structured locator and verification date;
- `witnesses`: Latin transcriptions bound to neutral uses, with coverage,
  independence and transcription identity;
- `collations`: the selected recension and text hash, witness set and compact
  apparatus result for one text.

Witness coverage is either the whole text, an explicit list of stable segment
ids, or an explicit list of stable word ids in canonical text order. Word-id
lists deliberately are not compressed to numeric ranges: ids record allocation
history rather than position, so a range could silently change meaning after a
later insertion.

`role`, `decision`, and acquisition state are separate facts. A strong official
edition does not support a claim merely by being relevant to its subject, and a
historical wording comparator is not thereby a source of the published
translation. Paginated evidence requires both printed and scan/PDF locators;
born-digital evidence requires a stable section. All ids are stable and URLs
never serve as identity.

Reader-facing role names describe only the function actually verified:
`official_text`, `direct_approved_print`, `official_liturgical_context`,
`historical_wording_basis`, `historical_wording_comparator`, and
`scripture_text`. The graph does not use a generic `historical_context` role:
age is not an evidentiary function, and a recent official edition may directly
print a much older prayer without becoming a historical study.

Wording uses live only in `languages/<lang>/bibliography.json`. A neutral use
cannot carry a wording role, and a language package cannot carry a neutral or
another language's use. The reader's neutral catalogue therefore contains only
neutral-reachable identities. A language artifact supplies a catalogue delta
for identities reached by that language alone, then a ready-to-render four-part
index: Latin textual sources, wording witnesses for the active language,
official documents and liturgical history, and Scripture/language/scholarship.

The reader projection is an allowlist. It omits evidence-image hashes,
owner-held inventory ids, migration pointers, editorial decisions and their
reasons, raw transcriptions, and archive paths. During the transition it emits
retained legacy citation attachments alongside the normalized projection.
Every legacy inline citation is held by a deterministic inventory digest and
may be claimed once by a normalized use or once by an explicit removal;
setting migration `complete` is rejected while any pointer remains unresolved.
A `migration.removals` entry therefore records an attachment excluded from the
published reader projection, not deletion of the canonical citation object
from the authored corpus. The build filters by exact legacy pointer (never by
source title), fails if a rejected attachment remains reader-visible, and
reports normalized-evidence coverage separately for the neutral, Polish, and
English packages.

The reader writes evidence as manifest-declared
`bibliography/texts/<category>/<text>.json` artifacts. Each slice contains the
projected evidence grouped by shared edition, digital item, role and locator,
plus witnesses and collation. The entries inside a source group retain their
stable use ids, local addresses and claims. Source ids resolve through the
manifest-declared package catalogue, which is loaded once rather than copied
into every text file. Language-specific
slices live under `languages/<lang>/bibliography/texts/` and contain only that
language's wording evidence; loading them alongside the neutral slice never
duplicates neutral uses. Global catalogues and functional indexes remain
separate manifest resources shared by the bibliography and text pages. The
functional index maps each source and role to text ids and use counts; detailed
claims stay in the lazily loaded text slices instead of being duplicated in the
index.

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

Word help must also be read as one card: the explanation, uncertainty note,
lemma note, displayed form, and gloss must agree. An explanation gives context
or sourced interpretation, while a disputed-reading note states the precise
remaining ambiguity. Do not repeat the same claim in both fields or describe
a form as two analyses "at once" when it merely permits either. Distinguish
morphology from theological interpretation. Attribute the latter to its source,
not to "this edition" as an authority. A grammatical reading may remain open
without making a cited doctrinal explanation sound equally uncertain.

`checks/prose.py` guards recognizable editorial self-reference in word help,
raw word IDs in plain notes, and exact explanation/note duplication. Semantic
agreement across the whole card still requires contextual review in each
language. Bibliographic references to an actual named edition are not banned.

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
  tombstone is permanent. The reader edition ships this map as `rw`.
- **A removed segment leaves a retirement record**:
  `"ids": {"segments": {"retired": {"s07": "s05"}}}`, naming the live
  segment that now carries its content. The reader edition ships the map
  (`rs` on the text artifact), so the app resolves a retired `?s=` address
  to the surviving verse and canonicalizes the link. Retirement records are
  permanent, and a retired id never returns to life. Both live and retired
  segment identifiers use the same `s` plus digits syntax; pre-contract
  semantic labels are not preserved as compatibility aliases. If a survivor
  is later retired, the older record remains unchanged and points through the
  newly added record; every acyclic chain must end at a live segment.
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
  Legacy composed witnesses use clause membership in the union of their named
  spans; that fallback does not prove order or multiplicity. A declared raw
  path with no local archive is an error.
- **Explicit raw bindings** use one `# raw-binding: <id>` header and an entry
  in `witnesses/raw/bindings.json` (version 1). Each archive records its full
  upstream path, exact revision, local raw path and SHA-256. Each witness entry
  records its path/revision, evidence ranges with section locations, reference
  lines and target evidence indexes, and ordered textual ranges. Its `path`
  header lists those evidence ranges exactly as `upstream [Section] (lines N-M)`
  separated by semicolons. Reference lines remain source evidence; no upstream
  runtime code is executed. The explicit reading plan must cover the selected
  textual evidence exactly once and contain no references or source framing.
  The whole witness body must equal that ordered reading, allowing only
  whitespace normalization and removal of line-initial source speaker markers.
  All punctuation, spelling, accents, case and ligatures are significant.
  Missing records/markers, drifted revisions/hashes/ranges, ambiguous identities,
  escaping paths, stale references and incomplete/reordered readings fail closed
  in transcription, archive and attribution checks. Deleting a marker does not
  downgrade a registered witness to legacy checking. New raw snapshots belong
  in subdirectories so existing top-level filename bindings remain unchanged.
- **`head`** and **`substantive`** (since 0.13.0) state the SYNTAX, which is
  the one thing that settles a reading the form permits and the sentence
  forbids. Every adjective, numeral and
  participle carries either `head`, the id of the word it must agree with, or
  `substantive: true`, meaning it agrees with nothing expressed — it heads its
  own phrase (*Salus infirmórum*, the health of the sick) or is impersonal
  (*postquam cenátum est*). A nominative adjective with an unexpressed subject/copula instead
  declares `ellipsis: "predicate"` and requires a localized contextual
  explanation. This explicitly reviewed elliptical predicate has neither a
  `head` nor `substantive`: it must not be attached to an unrelated finite verb
  merely to fill a field. The marker does not claim an expressed Latin subject.
  A nominative participle whose subject is understood, with no suitable expressed
  nominal controller or finite personal verb carrying that subject, may instead
  declare `ellipsis: "subject"`. This requires explicit case, number, gender,
  tense and voice plus a localized contextual explanation. It is neither
  substantivization nor a claim that a nearby impersonal verb has an omitted
  grammatical subject. It does not identify the theological referent by itself.
  It cannot also carry `head` or `substantive: true`. Apply it only after reading
  the complete construction; prefer a real agreement head when one is expressed.
  The validator constrains this claim's shape, not its contextual truth.
  Every preposition carries a `head` naming the word
  it governs. `checks/syntax.py` then verifies on every build that a modifier
  matches its head in case, number and gender, that a preposition's object
  stands in a case that preposition governs, and that a predicate complement or
  a nominative relative matches its verb in number.
  The lexicalized expressions *de/a/ab longe*, *ad invicem* and *ex tunc* attach
  to their adverbial complements and omit `governs`; they must not point to
  an unrelated declined word later in the sentence.
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
  parentheses?[], text? (rubric Latin), words?[] }`. **`speaker`** (since 0.9.0) is who says it —
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
  When literal source coverage fails, `checks/attribution_alignment.py` can
  separately establish attribution across exact declared one-to-one variants.
  This requires one complete verse, one unmarked explicitly bound source line,
  successful exact raw validation and full collation, and one complete
  unmodified witness supporting the entire selected reading. Every word is
  aligned ordinally; differing forms need exact source-specific rulings.
  Partial witnesses, corrigenda, recension removals, omissions, length-changing
  variants and multiline readings are ineligible. The result retains word
  mappings and source coordinates; the tool reports `ALIGNED`, never literal
  agreement. This authorizes only the existing unmarked-celebrant attribution;
  voice remains independently derived from the rubrics. Unresolved sources
  remain `UNSOURCED` and are never written.
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
  In a sung Passion the traditional parts use `chronista`, `christus`, and
  `synagoga`; the base speaker remains `sacerdos`, because at low Mass the
  celebrant reads the whole Passion.
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
- Segment **`parentheses`** (since 0.21.0) records genuine paired punctuation
  in the selected Latin, not directions, optional readings or target-language
  prose. Omit the field when unused. Otherwise it is a nonempty array of
  `{ "from": "w167", "through": "w170", "closing"?: "after-post" }`.
  Both inclusive endpoints must be live words in the same verse. Ranges follow
  document order (not numerical IDs) and must be sorted and disjoint: no
  duplicate, nested, crossing, shared-endpoint or cross-segment ranges. A
  single-word range is valid. No other keys or delimiter strings are accepted.
  The opening precedes the first lexical form; the closing normally precedes
  the last word's ordinary `post`, as in `(verbum),`. Explicit `after-post`
  instead gives `(verbum,)` and requires an actual valid `post` mark. Do not
  store an explicit default or empty array. Two ordinary marks around a
  closing, nesting, and cross-verse pairs require a future explicit contract,
  not silent deletion of attested punctuation.
  `checks/punctuation.py` projects exact prefix/form/suffix faces for collation
  and apparatus quotes, leaving every lexical word object and ID intact.
  Current translation-source payloads include the range field only when
  present; adding, moving or changing a pair invalidates that source binding.
  Existing payloads without ranges remain unchanged. Shape validation is not
  proof of a source reading. Raw-source framing adapters have a separate
  contract: their removal of bracketed directions cannot establish the
  integrity of a sacred parenthetical clause. Such raw sources need explicit
  source-framing support before that path can be used as evidence.
  Reader 5.7.0 transports the range as segment metadata, without new words or
  compact word fields. A reader-controlled excerpt must extend to include
  every intersected pair and render the real marks outside lexical forms;
  editorial ellipses follow the complete projected source, not a half-pair.
- Word: `{ id, form, post?, lemma, morph, analysis? }`. `post` = exactly one
  trailing punctuation mark rendered after the word (`,` `;` `:` `.` `?`
  `!`). It never carries a bracket, rubric, source marker, or two marks.
  `degree`
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
  `mood` (ind|subj|imp|inf|part|ger), `voice` (act|pass|dep), `conj` (1–4,
  omitted for irregulars such as sum, fio); preps: `governs` (acc|abl);
  intj covers indeclinables like Amen. **Participles** (since 0.8.0) are
  verb tokens with `mood: "part"`: no `person`, and they add the nominal
  agreement fields `case`/`number`/`gender` to `tense` (pres|perf|fut)
  and `voice` (deponent participles keep `voice: "dep"`, present as well as perfect).
  Gerundives and gerunds follow the distinct rules below.
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

### The gerund

The gerund is a verbal noun, not an agreeing gerundive. It is represented as
`pos: verb`, `mood: ger`, `voice: act`, `number: sg`, `gender: n`, with
`case: gen|dat|acc|abl` and the verb's `conj` where applicable. `tense: pres`
identifies its present-stem formation in the stored morphology; it does not
assert that the action takes place in the present. There is no `person`,
agreement `head`, or `substantive` modifier flag. The reader names the verbal
noun and its case rather than displaying it as a finite present-tense verb.

Deponent verbs also have active gerunds (Bennett §112a); their gerundives
remain passive (§112b). Thus `moriéndo` is an active ablative gerund, while
`ad imitándum ... exémplum` has a passive gerundive agreeing with exémplum.
A masculine actor does not make a gerund masculine. Context determines
gerund versus gerundive: `ad liberándum ... hóminem` can carry agreement,
whereas `ad protegéndum nos` has a verbal noun governing its plural object.
Do not rewrite biblical or later Latin to impose classical word order or
a different construction.

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
decides where the collation will accept it. Three classes settle one-to-one
differences in the LETTERS; each needs a nonempty ruling that quotes both
actual readings exactly, including their punctuation:

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
- **`substantive`** — a different lexical or grammatical reading, such as
  *inspexerunt* against *conspexerunt*, or *resurgemus* against *resurgamus*.
  The ruling explains the choice without misclassifying it as spelling or
  asserting a printer's slip. The selected reading must be positively
  attested at the aligned locus by another full witness, before corrigenda
  or apparatus substitutions. Reported separately as `substantive_variants=N`.
  This class cannot excuse a length mismatch or an accidental-only difference.
- **`substantive-span`** — a complete alternate phrase, including a genuine
  different-recension reading with a different number of words. `at` and
  `through` name the inclusive first and last stable word IDs **in document
  order**, not numerical ID order. `ours` is the exact space-joined sequence
  of their exact projected source tokens (`form` + `post` with any explicit
  paired punctuation); each `witnesses` value quotes that witness's
  entire actual phrase, including punctuation. A nonempty `ruling` explains
  the selection. For example:

  ```json
  {
    "at": "w060",
    "through": "w018",
    "ours": "ánimas famulórum famularúmque tuárum, quæ",
    "witnesses": {
      "do": "nostræ congregatiónis fratres, propínquos et benefactóres, qui"
    },
    "class": "substantive-span",
    "ruling": "Retain the complete reading of the controlling printed witness."
  }
  ```

  Here the document places the newly allocated IDs `w060`–`w063` before the
  retained `w018`. This example is a schema illustration, not source evidence.
  The checker consumes exactly the quoted alternate phrase at that locus;
  it does not search forward for a convenient matching substring. Every
  outside word still undergoes the ordinary substantive and accidental
  checks. Only a comparison buffer changes; source transcription bytes do
  not. The quote is exact even for a `substantive-only` witness.

  Another **single full raw witness** must attest all selected words at the
  same ordinal positions, before corrections or apparatus replacements.
  Its raw word count must equal the edition's, and it cannot declare an
  omission, a length-changing span, or a header recension removal. This is
  deliberately conservative: support requiring earlier length-changing
  alignment is not inferred. Accents, case, punctuation and ligatures use
  the ordinary substantive normalization for positive support; the support
  witness's own accidental differences remain subject to its usual checks.
  Partial witnesses, a union of separate witnesses' word readings, and
  circular replacements cannot supply positive support.

  Spans must not overlap each other, even across different witnesses. Put
  multiple alternate readings of one range in its `witnesses` map. A span
  also cannot overlap a single-word ruling for the same witness. Identical
  readings and accidental-only differences are rejected; so are missing or
  reversed endpoints, inaccurate quotes, and unused rulings. Quotes use
  single spaces, begin and end with lexical tokens, and cannot split one
  whitespace-delimited token into several words. Free-standing punctuation
  inside the quote is checked exactly. Separate word omissions can coexist
  outside a span; header recension removals in the same alternate witness
  cannot currently be combined with span alignment. Partial alternate
  witnesses may quote spans wholly within their declared coverage, but
  never replace either of the two required full witnesses.

  Counted once per alternate witness, not once per replaced word, within
  `substantive_variants=N`; the returned `substantive_spans` statistic gives
  that subset separately. These counts do not certify source transcription
  accuracy or editorial justification: those still require source review.
- **`omission`** — a full witness lacks a word printed by this edition and
  another full witness. Its witness reading is the empty string. The ruling
  must be nonempty and quote the exact selected token. Positive support must
  occur at the same locus in an uncorrected full witness, not be fabricated
  by another apparatus entry. Other differences still require their own
  exact rulings after omission alignment. Reported as `omissions=N`.
  An omission cannot be inferred from a partial witness.

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
- `decl_alt`: a second, distinct attested declension for a mixed-paradigm
  noun with a primary `decl` (ficus: `decl: 2`, `decl_alt: 4`). Each token
  records the paradigm of its actual form, not a list of alternatives.
  Both values must be integers from 1 through 5. This records a lexical
  fact; it does not establish a token's case, number or contextual reading.

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
segments{ <seg-id>: { translation, translation_citations? | narrative, alignments? } },
words{ <word-id>: { gloss?, explanation?, note? } }
```

- `about` (since 0.8.0; required for a published text): one short paragraph introducing the
  text — history, when it is prayed, structure — in the target language.
  Reader-facing and collapsed by default in apps; every claim must be
  true and verifiable (the quality doctrine applies as to any layer).
  Its presence is declared by the neutral core, not inferred from another
  target language.
- `about_citations` (since 0.11.0): optional reader-facing sources supporting
  the introduction. Since 0.16.0 these are written once in the neutral core.
- `gloss`: shortest natural reading aid in the target language
  (interlinear line). It may be idiomatic rather than grammatical — it is
  the sense the context selects, which no lemma-level sense list can supply.
  It is required unless the word belongs to an alignment on its segment.
  A visible gloss is always target-language wording: square-bracketed grammar
  labels, editorial placeholders, and dashes standing for silence are invalid.
- `alignments` (since 0.19.0; optional on a segment): the exceptional mapping
  between a contiguous source construction and its target-language realization.
  A realized alignment has `words` in source order, an `anchor` naming the
  source word whose analysis carries the shared reading, and one natural
  target-language `gloss`. It contains at least two words. For example:

  ```json
  { "words": ["w015", "w016"], "anchor": "w016", "gloss": "będzie" }
  ```

  A source particle with no separate target word omits `anchor` and `gloss`
  and declares why with `reason`: `idiom`, `inflection`, `punctuation`, or
  `word-order`. Every Latin word has exactly one realization: a direct gloss
  or membership in one alignment, never both. Alignments are language-specific,
  non-overlapping, contiguous, and stored in source order. Their purpose is to
  model real many-to-one or zero correspondences, not to conceal an unresolved
  translation.
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
