# Corpus schema v0 (0.5.0)

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
  order. Textual insertions get fresh IDs (policy TBD before public release:
  letter suffix `w012a` vs next-free-number).
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
- Segment: `{ id, type: "verse"|"rubric", text? (rubric Latin), words?[] }`.
- Word: `{ id, form, post?, lemma, morph, analysis? }`. `post` = trailing
  punctuation rendered after the word (`,` `;` `:` `.`). `lemma` is the key
  into `lexicon/lemmata.json` — dictionary-normalized (i-form,
  no j, full head: `ab` not `a`) and **lowercase except true proper names**
  (Maria, Michael, Ioannes, Baptista, Petrus, Paulus, Iesus — the linter's
  list); divine titles (deus, dominus, pater, spiritus) are lowercase
  common-noun lemmas. (0.4.0 removed the 0.2.0
  `tier` field: hand-judged per-word difficulty proved unreviewable.)
- `morph`: `pos` (verb|noun|adj|pron|adv|conj|prep|intj) plus per-pos fields —
  nouns/adjs/prons: `case` (nom|gen|dat|acc|abl|voc), `number` (sg|pl),
  `gender` (m|f|n), nouns also `decl` (1–5, omitted for Greek/irregular
  declensions such as Iesus); adjs: `degree` (comp|sup) when not positive;
  verbs: `person`, `number`, `tense` (pres|impf|fut|perf|plup|futperf),
  `mood` (ind|subj|imp|inf), `voice` (act|pass|dep), `conj` (1–4, omitted
  for irregulars such as sum, fio); preps: `governs` (acc|abl); intj covers
  indeclinables like Amen. Extend enums as texts require (participles etc.
  are not yet covered). Classification rulings: *sicut* is tagged `conj`
  (comparative conjunction) although several dictionaries head it as an
  adverb — analyzer disagreement at integration is expected there, not a
  silent error.

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
  with accents** (ORTHOGRAPHY.md applies to every component) — this is the
  display headword promised for j-lemmas (Joánnes for lemma `Ioannes`).
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

`lexicon/<lang>.json` (one per gloss language):

```
schema_version, lang, status, analysis_defaults,
entries{ <lemma>: { senses[], note?, analysis? } }
```

- `senses`: 1–4 short dictionary-style meanings in the target language,
  ordered by relevance to liturgical usage. Our own editorial wording —
  NEVER copied from protected dictionaries.
- `note`: optional lemma-level remark (etymology, register, usage) — facts
  true of the word everywhere. What used to be repeated on every token of
  `amen` lives here now.
- Language files must cover identical key sets (parity), which must equal
  the lemmata key set.

## Gloss document

```
schema_version, text, lang, status, analysis_defaults,
segments{ <seg-id>: { translation? | narrative? } },
words{ <word-id>: { gloss, function?, analysis? } }
```

- `gloss` (required): shortest natural reading aid in the target language
  (interlinear line). It may be idiomatic rather than grammatical — it is
  the sense the context selects, which no lemma-level sense list can supply.
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
