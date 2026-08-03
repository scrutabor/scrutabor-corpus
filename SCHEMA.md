# Corpus schema v0 (0.1.0)

Two layers per text: a language-neutral Latin source document and one gloss
document per language. JSON, UTF-8. `form` uses 1962 liturgical orthography
(u/v, j for consonantal i, æ/œ, accents — see ORTHOGRAPHY.md); `lemma` is
dictionary-normalized (i-form, no j) for analyzer matching. Normalization of
forms (strip accents, æ→ae, j→i) is derived mechanically, never stored.

## File layout

```
texts/<category>/<name>.json          Latin source + morphology
glosses/<lang>/<category>.<name>.json gloss layer (one per language)
```

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
  punctuation rendered after the word (`,` `:` `.`). `lemma` is a plain
  headword string until the lexicon exists — dictionary-normalized (i-form,
  no j) and **lowercase except true proper names** (Maria, Michael, Ioannes,
  Baptista, Petrus, Paulus — the linter's list); divine titles (deus,
  dominus) are lowercase common-noun lemmas. (0.4.0 removed the 0.2.0
  `tier` field: hand-judged per-word difficulty proved unreviewable.)
- `morph`: `pos` (verb|noun|adj|pron|adv|conj|prep) plus per-pos fields —
  nouns/adjs/prons: `case` (nom|gen|dat|acc|abl|voc), `number` (sg|pl),
  `gender` (m|f|n), nouns also `decl` (1–5); adjs: `degree` (comp|sup) when
  not positive; verbs: `person`, `number`, `tense` (pres|impf|fut|perf|plup|
  futperf), `mood` (ind|subj|imp|inf), `voice` (act|pass|dep), `conj` (1–4);
  preps: `governs` (acc|abl). Extend enums as texts require (participles etc.
  are not yet covered).

## Gloss document

```
schema_version, text, lang, status, analysis_defaults,
segments{ <seg-id>: { translation? | narrative? } },
words{ <word-id>: { gloss, function, analysis? } }
```

- `gloss`: shortest natural reading aid in the target language (interlinear
  line). It may be idiomatic rather than grammatical — the grammatical truth
  lives in `function`.
- `function`: 1–3 sentences answering "why this form here" in the target
  language, written for a reader with basic Latin. **Self-contained prose**
  — each entry is read in isolation. The only permitted cross-reference is
  the quoted-form pattern `„form” (wNNN)` (EN: `“form” (wNNN)`): the app
  renders the quoted form as a tap-link to that word and hides the id;
  bare ids in prose are lint errors.
- `narrative` (rubric segments): "what is happening at the altar" in the
  target language.
- `translation` (verse segments): our own working translation — NEVER copied
  from protected literary translations.
