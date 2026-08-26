# Terminology contract — gloss-language grammar vocabulary

Read before writing any contextual `explanation`; the linter enforces the
banned list and rejects stock grammatical openings that merely restate the
form row. An explanation is optional: keep it only when it helps a reader
understand the prayer's meaning, wording, imagery, source, or a genuine
translation difficulty. One term per concept, corpus-wide. Extend the tables
when new morphology appears (participles etc.); never introduce a synonym for
a term already listed.

## Polish

| concept | term | banned variants |
|---|---|---|
| cases with PL equivalents | mianownik, dopełniacz, celownik, biernik, wołacz | — |
| ablative (no PL case) | **ablativus** (odm. z „v”: ablativu, ablativie, ablativem, ablativów) | ablatiwus, ablatiw, ablatyw |
| deponent | deponens (opis: forma bierna, znaczenie czynne) | — |
| perfect | perfectum | czas przeszły dokonany (samodzielnie) |
| declension/conjugation | deklinacja I–V, koniugacja I–IV (rzymskie) | 1. deklinacja |
| apposition | apozycja (dopowiedzenie) — parenthetical at first mention per note or page; bare „apozycja” may follow anaphorically | przydawka rzeczowna |
| agreement claim | zgadza się z „…” | zgodny/zgodna/zgodne z |
| ablative of means | ablativus narzędzia | ablativus środka |
| ablative of cause | ablativus przyczyny | — |
| participle | imiesłów; z określeniami: imiesłów przyszły, imiesłów deponentny | imiesłów przymiotnikowy, participium (samodzielnie w prozie) |
| imperative | tryb rozkazujący | rozkaźnik |
| quotes in prose | „…” (polskie cudzysłowy) | "…", “…” |

## English

| concept | term | banned variants |
|---|---|---|
| cases | nominative, genitive, dative, accusative, ablative, vocative | — |
| declension/conjugation | 1st–5th declension, 1st–4th conjugation | Roman numerals |
| deponent | deponent (passive form, active meaning) | — |
| ablative of means / of cause | ablative of means, ablative of cause | — |
| participle | participle; qualified: future participle, deponent participle | verbal adjective (as the term) |
| quotes in prose | “…” (English quotes) | „…” |

## Linter hooks

`checks/lint.py` `BANNED_TERMS`: PL bans `ablatiw`, `ablativ* środka`,
`zgodn* z`, `rozkaźnik`; EN bans `„`.
Add a row here AND a pattern there when a new decision lands.

`REDUNDANT_EXPLANATION_OPENINGS` rejects templates such as “Wołacz jest…”
and “Dopełniacz liczby mnogiej…”. Case and agreement already belong to the
structured morphology; prose may mention them only when they unlock a real
ambiguity or a meaningful difference in translation.
