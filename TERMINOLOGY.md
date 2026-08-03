# Terminology contract — gloss-language grammar vocabulary

Read before writing any gloss `function` text; the linter enforces the banned
list. One term per concept, corpus-wide. Extend the tables when new
morphology appears (participles etc.); never introduce a synonym for a term
already listed.

## Polish

| concept | term | banned variants |
|---|---|---|
| cases with PL equivalents | mianownik, dopełniacz, celownik, biernik, wołacz | — |
| ablative (no PL case) | **ablativus** (odm. z „v”: ablativu, ablativie, ablativem, ablativów) | ablatiwus, ablatiw, ablatyw |
| deponent | deponens (opis: forma bierna, znaczenie czynne) | — |
| perfect | perfectum | czas przeszły dokonany (samodzielnie) |
| declension/conjugation | deklinacja I–V, koniugacja I–IV (rzymskie) | 1. deklinacja |
| apposition | apozycja (dopowiedzenie) | przydawka rzeczowna |
| quotes in prose | „…” (polskie cudzysłowy) | "…", “…” |

## English

| concept | term | banned variants |
|---|---|---|
| cases | nominative, genitive, dative, accusative, ablative, vocative | — |
| declension/conjugation | 1st–5th declension, 1st–4th conjugation | Roman numerals |
| deponent | deponent (passive form, active meaning) | — |
| quotes in prose | “…” (English quotes) | „…” |

## Linter hooks

`checks/lint.py` `BANNED_TERMS`: PL bans `ablatiw`; EN bans `„`.
Add a row here AND a pattern there when a new decision lands.
