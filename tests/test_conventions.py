"""The vocative is glossed bare (checks/conventions.py)."""

import json
from pathlib import Path

from checks.conventions import check

CORPUS = Path(__file__).resolve().parents[1]


def doc_with(*words):
    return {"id": "test.vocative", "segments": [{"id": "s01", "words": list(words)}]}


def voc(wid, form):
    return {"id": wid, "form": form, "lemma": "dominus", "morph": {"pos": "noun", "case": "voc"}}


def test_an_added_particle_on_a_vocative_is_refused():
    errors = check(
        doc_with(voc("w001", "Dómine")), {"lang": "en", "words": {"w001": {"gloss": "O Lord"}}}
    )
    assert len(errors) == 1 and "glossed bare" in errors[0]


def test_a_bare_vocative_and_a_printed_o_pass():
    o = {"id": "w001", "form": "O", "lemma": "o", "morph": {"pos": "intj"}}
    gloss = {"lang": "en", "words": {"w001": {"gloss": "O"}, "w002": {"gloss": "Lord"}}}
    assert check(doc_with(o, voc("w002", "Dómine")), gloss) == []


def test_a_non_vocative_may_begin_with_o():
    word = {"id": "w001", "form": "útinam", "lemma": "utinam", "morph": {"pos": "adv"}}
    assert check(doc_with(word), {"lang": "en", "words": {"w001": {"gloss": "O that"}}}) == []


def test_no_published_vocative_gloss_carries_the_particle():
    examined = 0
    for text_path in sorted((CORPUS / "texts").glob("*/*.json")):
        doc = json.loads(text_path.read_text(encoding="utf-8"))
        category, name = doc["id"].split(".", 1)
        for lang in ("en", "pl"):
            layer = CORPUS / "languages" / lang / "texts" / category / f"{name}.json"
            gloss = json.loads(layer.read_text(encoding="utf-8"))
            gloss.setdefault("lang", lang)
            examined += sum(
                (w.get("morph") or {}).get("case") == "voc"
                for s in doc["segments"]
                for w in s.get("words") or []
            )
            assert check(doc, gloss) == [], doc["id"]
    # the rule must have something to hold: the corpus addresses God and the
    # saints in hundreds of vocatives
    assert examined > 500
