# Orthography policy — 1962 liturgical (binding, corpus-wide)

Display `form` values follow the typical-edition 1962 liturgical books,
because the reader follows along in a physical 1962 hand missal and the
corpus must match what their eyes see.

## Rules

1. **u/v distinguished**: *vir*, *servus* — never the classical scholarly
   u-style (*uir*, *seruus*).
2. **i for consonantal i**: *Ioánni*, *eius*, *huius*, *Iesu* — not the
   j-style (*Joánni*, *ejus*). **Reversed 2026-08-06**, and the reversal
   is the point of the rule: it had said this edition prints j "as the
   1962 books print", and the 1962 books print i.
   The evidence, once the typical edition became a witness: the **Missale
   Romanum 1962** sets *Iesu*, *Ioánnem*, *iube*, *maiestátis*, *iunctis*,
   *eius* throughout (printed pages 302, 306, 307, 309, 327), and so does
   the **Ordo Missae of Pallottinum, Poznań 1963** — 1962 rubrics, Polish,
   imprimatur Karol Wojtyła — which prints *Dómini nostri Iesu Christi*
   and *Et in unum Dóminum Iesum Christum*. That second book decides it
   for this edition, because it is the one a Polish reader is likeliest to
   hold. The j-style is what the mid-century hand missals print, and what
   the Divinum Officium source files print; the apparatus records theirs.
   57 tokens under 27 forms were changed. Lemma keys were already i-form
   (rule 6), so the edition is now internally consistent as well.

3. **æ / œ ligatures** as printed: *beátæ*, *sǽcula*.
4. **Acute accents** mark the stressed syllable on words of three or more
   syllables; one- and two-syllable words are unaccented. Accents ARE
   printed on capital initials (*Ídeo*) — the omission in older books is a
   metal-type constraint, not doctrine, and stress position is exactly
   what the reader needs. Witnesses differ here; the apparatus records
   each ruling.
5. **V-for-U in capitals** (CVLPA, SVRSVM CORDA) is an inscriptional
   display convention — stone, façades, title pages. It never appears in
   running text and is not used in this corpus.
6. **Lemmas are dictionary-normalized**, deliberately unlike display
   forms: i-form (no j: *Ioannes*), lowercase except true proper names —
   so they match the conventions of morphological analyzers and dictionaries.
   Divine titles (*deus*, *dominus*) are lowercase common-noun lemmas.
7. **Diaeresis (ë)** as the typical editions print it, marking two vowels
   in hiatus where no acute already shows it: *Míchaël*, *Israël*, *Raphaël*.
   Oblique forms whose acute falls on the hiatus vowel need no diaeresis
   (*Michaélis*). ë counts as its own syllable and is not a stress accent.

## Witnesses and the apparatus

Every text names its witnesses (independent transcriptions or editions of
the same recension) in `witnesses/<text-id>/`, each file carrying a
provenance header. Collation enforces zero substantive divergence — the
letters must match. Where editions legitimately differ (punctuation,
capitalization, capital accents), each variant is recorded in
`apparatus.json` with the reading adopted, the witnesses' readings, and
the ruling. A variant without a ruling fails the build.

A witness must match the recension: the devotional Confiteor, for
instance, is a different text from the Ordo Missae Confiteor and cannot
serve as a witness for it.
