# Corpus schema v0 (0.10.0)

Three layers: a language-neutral Latin source document per text, one gloss
document per text per language, and a corpus-wide lexicon (language-neutral
lemma data + one sense file per language). JSON, UTF-8. `form` uses 1962
liturgical orthography (u/v, j for consonantal i, æ/œ, accents — see
ORTHOGRAPHY.md); `lemma` is dictionary-normalized (i-form, no j) for analyzer
matching. Normalization of forms (strip accents, æ→ae, j→i) is derived
mechanically, never stored.

Since 0.5.0 `schema_version` is corpus-wide: every document carries the same
number (earlier gloss documents versioned independently and stayed at 0.1.0).

## File layout

```
texts/<category>/<name>.json          Latin source + morphology
glosses/<lang>/<category>.<name>.json gloss layer (one per language)
lexicon/lemmata.json                  language-neutral lemma data
lexicon/<lang>.json                   senses per language
```

## The three layers of word help (binding division of labor)

Every fact lives in exactly one layer; a reader-facing sentence must not
restate what another layer already carries:

1. **Lexicon** (per lemma, written once): dictionary head, part of speech,
   paradigm data, senses, lemma-level notes (etymology, usage). True of the
   word everywhere.
2. **Morphology** (per token, structured): the `morph` object states THE
   parse in this context — apps render it as prose. This is where formal
   ambiguity (María vocative, not nominative) is resolved.
3. **`function` note** (per token, prose, OPTIONAL): only what is true of
   this word in this sentence and not derivable from the other two layers —
   see the gloss document section.

## Word IDs (binding rules)

- Global per text, zero-padded: `w001`… Referenced externally as
  `<text-id>.<word-id>` (e.g. `ordinarium.confiteor.w002`) by SRS decks and
  future GABC syllable maps (`w002.s1` reserved for syllables).
- **Never renumbered, never reused.** Document order = array order, not ID
  order. IDs are opaque stable tokens: the numeric appearance is allocation
  history, not position. A textual insertion takes the NEXT FREE NUMBER in
  its text, wherever it lands in reading order — the array carries the
  order, the ID carries only identity.
- Segment IDs (`s01`…) are NOT stable — segmentation may change freely; words
  are the stable layer.

## Latin source document

```
schema_version, id, title, category, section, variant, sung, status, notes,
analysis_defaults, segments[]
```

- `status`: `"working-edition"` until expert review (quality rule).
- `source` (since 0.3.0): provenance — how the text entered the corpus,
  pointer to its `witnesses/<text-id>/` directory and `apparatus.json`
  (adjudicated accidental variants). Collation (checks/collate.py)
  enforces zero substantive divergence from every witness.
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
- Segment: `{ id, type: "verse"|"rubric", speaker?, voice?, text? (rubric
  Latin), words?[] }`. **`speaker`** (since 0.9.0) is who says it —
  `sacerdos`, `minister`, `populus`, `omnes`, `schola` — and **`voice`**
  is how loudly: `clara` (aloud), `submissa` (raised but not full, the
  *elata aliquantulum voce* of Dómine non sum dignus), `secreto`
  (silently), `cantus` (sung). Both belong to verse segments only: a
  rubric is the edition's framing, not anyone's words.
  Both are READ from the sources by `checks/attribute.py`, never
  remembered. The speaker is read from the witnesses' markers — which come
  in both cases, the Ordo printing the priest's own Confiteor as a
  lowercase `v.` — aligned to the text IN ORDER, because a dialogue that
  repeats itself (the Kyrie's nine invocations of two phrases) cannot be
  read by content alone. Where a passage of the Mass carries no marker at
  all, the speaker is the celebrant: the Ordo marks every other voice, and
  the Ritus servandus names sacerdos as the actor throughout. Outside the
  Mass no such reasoning holds, so a devotional prayer takes only what an
  "all" marker gives it.
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
- Segment: **`participation`** (since 0.10.0) is who among the FAITHFUL makes
  this line, and on whose authority. `speaker` answers a different question —
  whom the Missale charges with the line — and at low Mass the answer is
  always the minister, which is true and is not what a person in the pew
  needs. The two must not be conflated: an edition that prints *ministrant*
  over the line a congregation is about to say has answered the wrong
  question.
  Shape: `{ lecta?: {gradus?, source}, cantu?: {gradus?, source} }`. The two
  keys are the two forms of Mass the law grades separately — `lecta` the low
  Mass, `cantu` the sung Mass — because they are not the same event, and a
  reader at a sung Sunday Mass has more of the Ordinary than one at a said
  Mass. `gradus` is the degree of participation, 1 to 4; it is ABSENT where
  the law grants a part without grading it (n. 32, the Pater noster).
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
  Conventions: nouns give the genitive (`mater, matris`; abbreviated for
  1st/2nd declension: `culpa, -æ`); adjectives give the feminine/neuter
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

`lexicon/<lang>.json` (one per gloss language):

```
schema_version, lang, status, analysis_defaults,
entries{ <lemma>: { senses[], note?, derivatives?, analysis? } }
```

- `senses`: 1–4 short dictionary-style meanings in the target language,
  ordered by relevance to liturgical usage. Our own editorial wording —
  NEVER copied from protected dictionaries.
- `note`: optional lemma-level remark (etymology, register, usage) — facts
  true of the word everywhere. What used to be repeated on every token of
  `amen` lives here now.
- `derivatives` (since 0.6.0): optional, 1–6 words of the TARGET language
  genuinely derived from or borrowed via this lemma (confíteor →
  konfesjonał; panis → companion) — memory hooks for learners. Only real
  descent counts; lookalikes and independent cognates do not (mors is NOT
  the source of Polish "mord"). A word that descends through the lemma's
  base or a sibling of the same root family, rather than through the
  lemma itself, names its true ancestor in parentheses: „kustosz (od
  custos)”, "custody (from custódia)". Per-language by nature: no parity
  requirement, and entries differ freely between languages.
- Language files must cover identical key sets (parity), which must equal
  the lemmata key set.

## Gloss document

```
schema_version, text, lang, status, about?, analysis_defaults,
segments{ <seg-id>: { translation? | narrative? } },
words{ <word-id>: { gloss, function?, analysis? } }
```

- `about` (since 0.8.0, optional): one short paragraph introducing the
  text — history, when it is prayed, structure — in the target language.
  Reader-facing and collapsed by default in apps; every claim must be
  true and verifiable (the quality doctrine applies as to any layer).
  Presence parity across languages per text (lint-enforced): the claim
  set is about the Latin text, not about the gloss language.
- `gloss` (required): shortest natural reading aid in the target language
  (interlinear line). It may be idiomatic rather than grammatical — it is
  the sense the context selects, which no lemma-level sense list can supply.
  A token whose sense a neighboring word's gloss has absorbed (the
  auxiliary of a periphrastic whose participle glosses the whole tense)
  glosses as an em dash `—`: the declared interlinear null.
- `function` (OPTIONAL, contextual-only): 1–3 sentences on what this word
  does **in this sentence**, in the target language, for a reader with basic
  Latin. Belongs here: agreement ("agrees with «culpa»"), apposition,
  government ("ablative after «pro»"), implied verbs, resolution of formal
  ambiguity (culpă/culpā), word order, idiom, scriptural or liturgical
  resonance of the phrase. Does NOT belong here: bare parse restatements
  (the morph layer renders those) or lemma-level facts (the lexicon carries
  those). Naming a case is fine when the case is the hinge of the claim
  ("vocative, not dative — direct address"), never as a standalone label.
  Omit the key entirely when the parse and lexicon already say everything —
  presence must agree across languages (the claim is about the Latin, not
  about the gloss language). **Self-contained prose** — each entry is read
  in isolation. The only permitted cross-reference is the quoted-form
  pattern `„form” (wNNN)` (EN: `“form” (wNNN)`): the app renders the quoted
  form as a tap-link to that word and hides the id; bare ids in prose are
  lint errors.
- `narrative` (rubric segments): "what is happening at the altar" in the
  target language.
- `translation` (verse segments): our own working translation — NEVER copied
  from protected literary translations.
