"""The two Greater-Litanies commemoration orations: exact bodies, declared same-edition
composite witnesses, bounded source claims, pending reviews, captions, declarations and lexicon
companions. Finite pins for these two children, not a rule for other texts."""

import json
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import digest, selected_text, transcript_digest
from build_reader.layers import expand_core
from checks import transcription
from checks.collate import collate
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
LM = "proprium.litaniae-maiores-"
COLLECT, POSTCOMMUNION = LM + "collecta", LM + "postcommunio"
TEXTS = [COLLECT, POSTCOMMUNION]
BODY = {COLLECT: 20, POSTCOMMUNION: 21}
LATIN = {
    COLLECT: (
        "Præsta, quǽsumus, omnípotens Deus: ut qui in afflictióne nostra de tua pietáte "
        "confídimus; contra advérsa ómnia, tua semper protectióne muniámur. Per Dóminum nostrum "
        "Iesum Christum, Fílium tuum, qui tecum vivit et regnat in unitáte Spíritus Sancti, "
        "Deus, per ómnia sǽcula sæculórum. Amen."
    ),
    POSTCOMMUNION: (
        "Vota nostra, quǽsumus, Dómine, pio favóre proséquere: ut, dum dona tua in tribulatióne "
        "percípimus, de consolatióne nostra in tuo amóre crescámus. Per Dóminum nostrum Iesum "
        "Christum, Fílium tuum, qui tecum vivit et regnat in unitáte Spíritus Sancti, Deus, per "
        "ómnia sǽcula sæculórum. Amen."
    ),
}
MR = (
    "Missale Romanum, Benziger Brothers, New York, 1962, Editio iuxta typicam; declared "
    "same-edition composite"
)
VATICAN = (
    "Missale Romanum, Vatican editio typica, Saint Joseph-bearing reproduction; production year "
    "not established; declared same-edition composite"
)
ACCIDENTALS = {
    COLLECT: [
        ("w005", "ut", {"vatican": "ut,"}, "punctuation"),
        ("w022", "Dóminum", {"mr": "Dominum"}, "accent"),
        ("w025", "Christum,", {"mr": "Christum"}, "punctuation"),
        ("w026", "Fílium", {"mr": "Filium"}, "accent"),
        ("w034", "unitáte", {"mr": "unitate"}, "accent"),
        ("w035", "Spíritus", {"mr": "Spiritus"}, "accent"),
        ("w039", "ómnia", {"mr": "omnia"}, "accent"),
        ("w040", "sǽcula", {"mr": "sæcula"}, "accent"),
        ("w041", "sæculórum.", {"mr": "sæculorum."}, "accent"),
        ("w042", "Amen.", {"mr": "Amen;", "vatican": "Amen;"}, "punctuation"),
    ],
    POSTCOMMUNION: [
        ("w023", "Dóminum", {"mr": "Dominum"}, "accent"),
        ("w026", "Christum,", {"mr": "Christum"}, "punctuation"),
        ("w027", "Fílium", {"mr": "Filium"}, "accent"),
        ("w035", "unitáte", {"mr": "unitate"}, "accent"),
        ("w036", "Spíritus", {"mr": "Spiritus"}, "accent"),
        ("w040", "ómnia", {"mr": "omnia"}, "accent"),
        ("w041", "sǽcula", {"mr": "sæcula"}, "accent"),
        ("w042", "sæculórum.", {"mr": "sæculorum."}, "accent"),
        ("w043", "Amen.", {"mr": "Amen;", "vatican": "Amen;"}, "punctuation"),
    ],
}
ABOUT = {
    ("pl", COLLECT): "Kolekta wspomnienia Litanii Większych w Mszale Rzymskim z 1962 roku.",
    (
        "en",
        COLLECT,
    ): "The collect for the commemoration of the Greater Litanies in the 1962 Roman Missal.",
}
NOTE = {
    "pl": (
        "Przyjmowane dary i doświadczana pociecha uzasadniają prośbę o wzrost miłości do Boga. "
        "Samo tuo nie rozstrzyga, czy chodzi o miłość do Boga, czy o Jego miłość."
    ),
    "en": (
        "Receiving God’s gifts amid tribulation and experiencing consolation support the petition "
        "for growth in love for God. The possessive tuo alone does not decide between love for God "
        "and God’s love."
    ),
}
MEASURED = {
    COLLECT: {"w002": ["editorial"], "w008": ["editorial"], "w019": ["editorial", "collatinus"]},
    POSTCOMMUNION: {"w003": ["editorial"]},
}


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def core(text):
    return load("texts/" + text.replace(".", "/", 1) + ".json")


def layer(language, text):
    return load(f"languages/{language}/texts/" + text.replace(".", "/", 1) + ".json")


def words(doc):
    return [word for segment in doc["segments"] for word in segment["words"]]


def record(section, identifier):
    (found,) = [row for row in load("bibliography/graph.json")[section] if row["id"] == identifier]
    return found


@pytest.mark.parametrize("text", TEXTS)
def test_the_body_and_the_supplied_conclusion_are_exactly_inventoried(text):
    doc = core(text)
    body = BODY[text]
    first, amen = doc["segments"]
    assert [s["id"] for s in doc["segments"]] == ["s01", "s02"]
    assert len(first["words"]) == body + 21 and len(amen["words"]) == 1
    assert doc["ids"] == {"next": body + 23, "segments": {"next": 3}}
    assert " ".join(w["form"] + w.get("post", "") for w in words(doc)) == LATIN[text]
    cue = first["words"][body]
    assert (cue["form"], cue["lemma"], cue["head"]) == ("Per", "per", f"w{body + 2:03d}")
    relative = first["words"][body + 7]
    assert (relative["form"], relative["lemma"], first["words"][body + 6]["post"]) == (
        "qui",
        "qui",
        ",",
    )
    assert amen["words"][0] == {
        "form": "Amen",
        "lemma": "amen",
        "morph": {"pos": "intj"},
        "post": ".",
        "id": f"w{body + 22:03d}",
    }
    assert (first["speaker"], first["voice"], first["delivery"]) == (
        "sacerdos",
        "clara",
        {"cantu": {"speaker": "sacerdos", "voice": "cantus"}},
    )
    assert (amen["speaker"], amen["voice"], amen["delivery"]) == (
        "minister",
        "clara",
        {"cantu": {"speaker": "schola", "voice": "cantus"}},
    )
    assert doc["variant"] == "litaniae-maiores" and doc["sung"] is False


def test_the_two_children_use_forty_four_lemmata_including_the_two_new_ones():
    lemmata = {w["lemma"] for text in TEXTS for w in words(core(text))}
    assert len(lemmata) == 44 and {"afflictio", "favor"} <= lemmata
    assert sum(len(words(core(text))) for text in TEXTS) == 85


@pytest.mark.parametrize("text", TEXTS)
def test_the_witnesses_are_declared_same_edition_composites(text):
    directory = ROOT / "witnesses" / text
    assert collate(expand_core(core(text)), directory)[:2] == ([], [])
    assert transcription.check_transcriptions(directory)[0] == []
    for name, description in (("mr", MR), ("vatican", VATICAN)):
        lines = (directory / f"{name}.txt").read_text(encoding="utf-8").splitlines()
        headers = [line for line in lines if line.startswith("#")]
        (body,) = [line for line in lines if line and not line.startswith("#")]
        assert headers[0] == f"# witness: {name}" and headers[1] == f"# description: {description}"
        assert any(
            h.startswith(
                f"# composite: proper body of {BODY[text]} words followed by the separately printed"
            )
            for h in headers
        )
        assert any(
            h.startswith("# independence: two loci of this edition form one witness")
            for h in headers
        )
        assert any(h.startswith("# actor-limit: no invented S./R. markers") for h in headers)
        assert body.endswith("Amen;")
    mr = (directory / "mr.txt").read_text(encoding="utf-8")
    vatican = (directory / "vatican.txt").read_text(encoding="utf-8")
    assert (
        "Per Dominum nostrum Iesum Christum Filium tuum, qui tecum vivit et regnat in unitate" in mr
    )
    assert (
        "Per Dóminum nostrum Iesum Christum, Fílium tuum, qui tecum vivit et regnat in unitáte"
        in vatican
    )
    apparatus = load(f"witnesses/{text}/apparatus.json")
    assert apparatus["summary"] == {
        "entries": len(ACCIDENTALS[text]),
        "classes": ["accent", "punctuation"],
    }
    assert [
        (e["at"], e["ours"], e["witnesses"], e["class"]) for e in apparatus["adjudicated"]
    ] == ACCIDENTALS[text]
    assert all(e["ruling"] for e in apparatus["adjudicated"])


@pytest.mark.parametrize("text", TEXTS)
def test_the_graph_records_stay_bounded_and_pending(text):
    doc = core(text)
    for edition, role in (
        ("mr1962", "official_text"),
        ("vatican1962", "corroborating_latin_witness"),
    ):
        page = record("uses", f"use.{text}.{edition}")
        rule = record("uses", f"use.{text}.conclusion-rg115a.{edition}")
        assert page["role"] == role and rule["role"] == "rubric_control"
        assert page["address"] == rule["address"] == {"kind": "text", "text": text}
        assert "are not printed in full on this proper page" in page["claim"]
        assert "abbreviated Per Dominum cue" in page["claim"]
        assert rule["locator"]["section"].startswith("Rubricae generales115a")
        assert "not printed continuously on the proper page" in rule["claim"]
        assert page["decision"] == rule["decision"] == "RETAIN"
        witness = record("witnesses", f"witness.{text}.{edition}")
        transcript = (ROOT / "witnesses" / text / f"{witness['transcription']}.txt").read_text(
            encoding="utf-8"
        )
        assert witness["transcription_sha256"] == transcript_digest(transcript)
        assert witness["orthography_profile"] == "literal-declared-same-edition-composite"
        assert witness["coverage"] == {"kind": "full"}
        assert witness["source_dependencies"] == {"uses": [rule["id"]], "raw_binding": None}
        assert witness["review"] == {"status": "pending"}
    assert record("witnesses", f"witness.{text}.mr1962")["role"] == "controlling"
    assert record("witnesses", f"witness.{text}.vatican1962")["role"] == "approved_corroboration"
    collation = record("collations", f"collation.{text}.mr1962-vatican1962")
    assert collation["witnesses"] == [f"witness.{text}.mr1962", f"witness.{text}.vatican1962"]
    assert collation["selected_text_sha256"] == digest(selected_text(doc))
    assert collation["apparatus_sha256"] == digest(load(f"witnesses/{text}/apparatus.json"))
    assert collation["apparatus"] == {
        "entries": len(ACCIDENTALS[text]),
        "classes": ["accent", "punctuation"],
    }
    assert collation["review"] == {"status": "pending"}


def test_the_captions_keep_the_sentence_internal_relative_and_the_english_group():
    polish, english = layer("pl", COLLECT), layer("en", COLLECT)
    assert polish["words"]["w006"] == {"gloss": "my, którzy"} and english["words"]["w006"] == {
        "gloss": "we who"
    }
    assert polish["words"]["w028"] == {"gloss": "który"} and english["words"]["w028"] == {
        "gloss": "who"
    }
    assert (polish["about"], english["about"]) == (ABOUT["pl", COLLECT], ABOUT["en", COLLECT])
    polish, english = layer("pl", POSTCOMMUNION), layer("en", POSTCOMMUNION)
    assert polish["words"]["w029"] == {"gloss": "który"} and english["words"]["w029"] == {
        "gloss": "who"
    }
    (opening,) = [a for a in english["segments"]["s01"]["alignments"] if a["words"][0] == "w001"]
    assert opening == {
        "words": [f"w{i:03d}" for i in range(1, 8)],
        "anchor": "w007",
        "gloss": "Attend to our prayers with loving favor, we pray, O Lord",
    }
    assert polish["words"]["w020"] == {"explanation": NOTE["pl"]}
    assert english["words"]["w020"] == {"explanation": NOTE["en"]}
    for language in ("pl", "en"):
        for text in TEXTS:
            assert layer(language, text)["segments"]["s02"] == {"translation": "Amen."}
    assert core(COLLECT)["localization"] == {"about": True}
    assert core(POSTCOMMUNION)["localization"] == {"about": True, "explanations": {"w020": {}}}


def test_the_lexicon_companions_are_the_adopted_ones():
    lemmata = load("lexicon/lemmata.json")["entries"]
    analysis = {"confidence": "high", "sources": ["editorial"], "review": "pending"}
    assert lemmata["afflictio"] == {
        "head": "afflíctio, afflictiónis",
        "pos": "noun",
        "gender": "f",
        "decl": 3,
        "analysis": analysis,
    }
    assert lemmata["favor"] == {
        "head": "favor, favóris",
        "pos": "noun",
        "gender": "m",
        "decl": 3,
        "analysis": analysis,
    }
    assert lemmata["amen"]["localization"]["note_citations"][0]["locator"] == "s.v. amen, III.A–B"
    polish, english = (
        load("languages/pl/lexicon.json")["entries"],
        load("languages/en/lexicon.json")["entries"],
    )
    assert polish["afflictio"] == {"senses": ["utrapienie, cierpienie"]}
    assert polish["favor"] == {"senses": ["przychylność, życzliwość"]}
    assert english["afflictio"] == {"senses": ["affliction, suffering"]}
    assert english["favor"] == {"senses": ["favor, goodwill"]}
    assert list(polish) == list(english) == list(lemmata)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_the_manifest_and_the_ledger_carry_the_children(language):
    manifest = load(f"languages/{language}/manifest.json")["texts"]
    assert manifest.index(COLLECT) + 1 == manifest.index(POSTCOMMUNION)
    assert manifest.index("proprium.in-octava-nativitatis-secreta") < manifest.index(COLLECT)
    sites = {
        s["site"]: s for s in load(f"languages/{language}/translation-provenance.json")["sites"]
    }
    for text in TEXTS:
        doc, lay = core(text), layer(language, text)
        for segment in doc["segments"]:
            site = sites[f"{text}.{segment['id']}.{language}"]
            assert site["origin"] == ("trivial" if segment["id"] == "s02" else "working-unsettled")
            assert site["review"] == "working" and site["familiar_core"] is False
            assert site["source_sha256"] == canonical_hash(source_payload(segment))
            assert site["target_sha256"] == canonical_hash(
                lay["segments"][segment["id"]]["translation"]
            )


@pytest.mark.parametrize("text", TEXTS)
def test_the_analysis_declarations_follow_the_measured_confirmers(text):
    editorial = core(text)["editorial"]
    assert editorial["status"] == "working-edition"
    assert editorial["analysis_defaults"] == {
        "confidence": "medium",
        "sources": ["editorial"],
        "review": "pending",
    }
    assert editorial["analysis_defaults_words"] == {
        "confidence": "medium",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }
    assert editorial["words"] == {
        word: {"analysis": {"confidence": "medium", "sources": sources, "review": "pending"}}
        for word, sources in MEASURED[text].items()
    }
    assert (
        "same-edition" in editorial["source"]["method"] or "RG115a" in editorial["source"]["method"]
    )
    assert editorial["source"]["witnesses"] == f"witnesses/{text}/"
