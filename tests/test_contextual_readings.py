"""Contextual homonyms and names that a suffix or agreement check cannot settle."""

import json
from pathlib import Path

import pytest

CORPUS = Path(__file__).resolve().parents[1]


def test_andrew_epistle_preserves_the_printed_participle_and_declares_the_digital_error():
    from checks.collate import load_witness

    tid = "proprium.sancti-andreae-apostoli-epistola"
    directory = CORPUS / "witnesses" / tid
    _, printed = load_witness(directory / "mr.txt")
    metadata, digital = load_witness(directory / "do.txt")
    assert "evangelizántium bona" in printed
    assert "evangelizándum bona" in digital
    assert metadata["corrigenda"][0][:2] == ("evangelizándum", "evangelizántium")
    token = word(tid.replace(".", "/", 1), "w080")
    assert token["form"] == "evangelizántium"
    assert token["morph"] == {
        "pos": "verb",
        "case": "gen",
        "gender": "m",
        "number": "pl",
        "tense": "pres",
        "voice": "act",
        "mood": "part",
        "conj": 1,
    }
    assert word(tid.replace(".", "/", 1), "w077")["morph"]["case"] == "nom"


def word(text, identifier):
    doc = json.loads((CORPUS / "texts" / f"{text}.json").read_text())
    return next(w for s in doc["segments"] for w in s.get("words", []) if w["id"] == identifier)


def test_annunciation_paschal_pair_keeps_ave_and_restores_virga():
    from checks.collate import load_witness

    tid = "proprium.annuntiatio-beatae-mariae-virginis-alleluia"
    relative = tid.replace(".", "/", 1)
    doc = json.loads((CORPUS / "texts" / f"{relative}.json").read_text())
    tokens = doc["segments"][0]["words"]
    assert [w["id"] for w in tokens] == [f"w{i:03}" for i in range(43, 73)]
    assert doc["ids"]["next"] == 73
    assert doc["ids"]["retired"] == {f"w{i:03}": "s01" for i in range(1, 43)}
    assert [w["form"] for w in tokens[13:16]] == ["Virga", "Iesse", "flóruit"]
    assert word(relative, "w046")["morph"]["case"] == "voc"
    assert word(relative, "w047")["morph"]["case"] == "abl"
    assert word(relative, "w048")["morph"]["case"] == "voc"
    assert word(relative, "w048")["head"] == "w046"
    assert word(relative, "w069")["head"] == "w065"
    assert word(relative, "w070")["lemma"] == "imus"
    assert word(relative, "w070")["morph"]["case"] == "acc"
    assert word(relative, "w071")["morph"]["case"] == "dat"
    for identifier in ("w070", "w071"):
        token = word(relative, identifier)
        assert token["morph"]["degree"] == "sup"
        assert token["substantive"] is True
    _, printed = load_witness(CORPUS / "witnesses" / tid / "mr.txt")
    _, digital = load_witness(CORPUS / "witnesses" / tid / "do.txt")
    assert "Post partum" not in printed
    assert "Virga Iesse flóruit" in printed
    assert "Virga Jesse flóruit" in digital
    assert printed != digital


def test_annunciation_targets_cover_both_paschal_verses_and_mark_shared_formula():
    tid = "proprium.annuntiatio-beatae-mariae-virginis-alleluia"
    for language, phrases in [
        ("pl", ["Zdrowaś Maryjo", "Różdżka Jessego zakwitła", "Bóg przywrócił pokój"]),
        ("en", ["Hail Mary", "The shoot of Jesse has blossomed", "God has restored peace"]),
    ]:
        layer = json.loads(
            (
                CORPUS / "languages" / language / "texts" / (tid.replace(".", "/", 1) + ".json")
            ).read_text()
        )
        assert all(phrase in layer["segments"]["s01"]["translation"] for phrase in phrases)
        assert set(layer["words"]) == {f"w{i:03}" for i in range(43, 73)}
        provenance = json.loads(
            (CORPUS / "languages" / language / "translation-provenance.json").read_text()
        )
        site = next(s for s in provenance["sites"] if s["site"] == f"{tid}.s01.{language}")
        assert site["familiar_core"] is True
        assert site["origin"] != "own"


@pytest.mark.parametrize(
    "name",
    [
        "annuntiatio-beatae-mariae-virginis-evangelium",
        "beata-maria-virgo-regina-evangelium",
        "beatae-mariae-virginis-a-rosario-evangelium",
        "immaculata-conceptio-evangelium",
    ],
)
def test_luke_greeting_addresses_mary_not_the_ablative_grace(name):
    relative = "proprium/" + name
    plena = word(relative, "w039")
    assert plena["morph"] == {"pos": "adj", "case": "voc", "gender": "f", "number": "sg"}
    assert plena["substantive"] is True
    assert "head" not in plena
    assert word(relative, "w038")["morph"]["case"] == "abl"


def test_immaculate_offertory_plena_agrees_with_its_vocative_maria():
    relative = "proprium/immaculata-conceptio-offertorium"
    plena = word(relative, "w004")
    assert plena["morph"]["case"] == "voc"
    assert plena["head"] == "w002"
    assert word(relative, "w002")["morph"]["case"] == "voc"
    assert word(relative, "w003")["morph"]["case"] == "abl"


@pytest.mark.parametrize(
    "name,number",
    [
        ("beatae-mariae-virginis-a-rosario-introitus", 23),
        ("dominica-infra-octavam-nativitatis-graduale", 13),
        ("immaculatum-cor-beatae-mariae-virginis-introitus", 17),
        ("sanctae-annae-matris-beatae-mariae-virginis-introitus", 22),
        ("transfiguratio-domini-graduale", 13),
        ("visitatio-beatae-mariae-virginis-introitus", 15),
    ],
)
def test_psalm_44_has_a_heart_subject_works_object_and_king_recipient(name, number):
    relative = "proprium/" + name
    cor = word(relative, f"w{number:03}")
    meum = word(relative, f"w{number + 1:03}")
    mea = word(relative, f"w{number + 7:03}")
    regi = word(relative, f"w{number + 8:03}")
    assert cor["morph"]["case"] == "nom"
    assert meum["head"] == cor["id"]
    assert "substantive" not in meum
    assert mea["morph"] == {"pos": "adj", "case": "acc", "number": "pl", "gender": "n"}
    assert mea["head"] == f"w{number + 6:03}"
    assert regi["lemma"] == "rex"
    assert regi["morph"] == {"pos": "noun", "case": "dat", "gender": "m", "number": "sg", "decl": 3}


def test_anne_tract_is_not_the_preceding_gradual_and_keeps_retired_addresses():
    text = "proprium/sanctae-annae-matris-beatae-mariae-virginis-tractus"
    doc = json.loads((CORPUS / "texts" / f"{text}.json").read_text())
    assert [s["id"] for s in doc["segments"]] == ["s02"]
    assert len(doc["segments"][0]["words"]) == 37
    assert doc["ids"]["segments"]["retired"] == {"s01": "s02"}
    assert doc["ids"]["retired"] == {f"w{i:03}": "s02" for i in range(1, 26)}
    assert doc["ids"]["next"] == 63
    assert word(text, "w027")["morph"]["case"] == "voc"
    assert word(text, "w044")["morph"]["case"] == "acc"
    assert word(text, "w052")["head"] == "w051"
    assert word(text, "w059")["lemma"] == "prospere"
    assert word(text, "w059")["morph"] == {"pos": "adv"}
    assert word(text, "w062")["lemma"] == "regno"
    assert word(text, "w062")["morph"]["mood"] == "imp"


def test_anne_targets_do_not_import_martyrdom_or_a_command_to_fight():
    relative = "texts/proprium/sanctae-annae-matris-beatae-mariae-virginis-tractus.json"
    pl = json.loads((CORPUS / "languages/pl" / relative).read_text())
    en = json.loads((CORPUS / "languages/en" / relative).read_text())
    assert "shed your blood" not in en["segments"]["s02"]["translation"]
    assert "ride on triumphant" not in en["segments"]["s02"]["translation"]
    assert "proceed prosperously, and reign" in en["segments"]["s02"]["translation"]
    assert "walcz" not in pl["segments"]["s02"]["translation"]
    assert pl["words"]["w040"]["gloss"] == "znienawidziłaś"
    assert pl["words"]["w041"]["gloss"] == "nieprawość"
    assert pl["words"]["w044"]["gloss"] == "cię"
    assert pl["words"]["w047"]["gloss"] == "twój"


def test_anne_alleluia_has_a_nominative_passive_subject_and_accusative_addressee():
    text = "proprium/sanctae-annae-matris-beatae-mariae-virginis-alleluia"
    assert word(text, "w003")["morph"]["case"] == "nom"
    assert word(text, "w003")["head"] == "w005"
    assert word(text, "w005")["morph"]["case"] == "nom"
    assert word(text, "w008")["morph"]["case"] == "abl"
    assert word(text, "w008")["head"] == "w007"
    assert word(text, "w011")["morph"]["case"] == "acc"


def test_seven_sorrows_has_its_own_source_bound_tract():
    from checks.collate import load_witness

    tid = "proprium.septem-dolorum-beatae-mariae-virginis-tractus"
    core = json.loads((CORPUS / "texts" / (tid.replace(".", "/", 1) + ".json")).read_text())
    assert len(core["segments"][0]["words"]) == 31
    assert core["segments"][0]["words"][0]["form"] == "Stabat"
    parent = json.loads(
        (CORPUS / "formularies/sanctorale/septem-dolorum-beatae-mariae-virginis.json").read_text()
    )
    tract = next(c for c in parent["components"] if c["key"] == "tractus")
    assert (tract["text"], tract["relation"]) == (tid, "proper")
    assert tract["condition"] == {"use": "votive-after-septuagesima"}
    _, printed = load_witness(CORPUS / "witnesses" / tid / "mr.txt")
    _, digital = load_witness(CORPUS / "witnesses" / tid / "do.txt")
    assert "transítis" in printed and "tránsitis" in digital
    assert "iuxta crucem" in printed and "juxta Crucem" in digital
    graph = json.loads((CORPUS / "bibliography/graph.json").read_text())
    continuation = next(u for u in graph["uses"] if u["id"] == f"use.{tid}.mr1962-continuation")
    assert continuation["address"]["word"] == "w008"
    assert continuation["locator"]["printed"] == "p. 671"
    assert (
        continuation["evidence_sha256"]
        == "2a6a0c6fefd1980b7d11b495c30ed0c27eff5897b418d3b32209e5cc4b364e14"
    )


def test_seven_sorrows_address_is_not_a_verb_object_and_enquiry_is_not_a_condition():
    text = "proprium/septem-dolorum-beatae-mariae-virginis-tractus"
    for identifier in ["w017", "w018"]:
        assert word(text, identifier)["morph"]["case"] == "voc"
    assert word(text, "w019")["morph"]["case"] == "nom"
    assert word(text, "w015")["head"] == "w003"
    assert word(text, "w027")["morph"]["mood"] == "ind"
    pl, en = layer("pl", text), layer("en", text)
    assert pl["words"]["w026"]["gloss"] == "czy"
    assert en["words"]["w026"]["gloss"] == "whether"
    assert pl["words"]["w010"]["gloss"] == "krzyżu"
    assert pl["words"]["w020"]["gloss"] == "przechodzicie"
    assert en["words"]["w020"]["gloss"] == "pass"
    zero = next(a for a in pl["segments"]["s01"]["alignments"] if a["words"] == ["w016"])
    assert zero == {"words": ["w016"], "reason": "idiom"}


def test_september_sorrows_collect_keeps_its_own_shorter_recension():
    text = "proprium/septem-dolorum-beatae-mariae-virginis-collecta"
    core = json.loads((CORPUS / "texts" / (text + ".json")).read_text())
    words = [w for s in core["segments"] for w in s.get("words", [])]
    assert len(words) == 47
    assert core["ids"]["next"] == 61
    assert core["ids"]["retired"] == {f"w{i:03}": "s01" for i in [22, 24, 25, *range(28, 38)]}
    assert word(text, "w060")["form"] == "dolóres"
    assert word(text, "w021")["morph"]["number"] == "pl"
    assert word(text, "w021")["head"] == "w027"
    assert word(text, "w023")["morph"]["gender"] == "f"
    assert word(text, "w026")["lemma"] == "veneror"
    assert word(text, "w026")["morph"]["mood"] == "ger"
    assert "transfixiónem" not in [w["form"] for w in words]


def test_english_sword_card_does_not_teach_only_the_remote_fish_sense():
    lexicon = json.loads((CORPUS / "languages/en/lexicon.json").read_text())
    assert "sword" in lexicon["entries"]["gladius"]["senses"]


def test_requiem_tract_preserves_the_printed_dead_and_declares_the_digital_omission():
    from checks.collate import load_witness

    tid = "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-tractus"
    directory = CORPUS / "witnesses" / tid
    _, printed = load_witness(directory / "mr.txt")
    _, digital = load_witness(directory / "do.txt")
    assert "fidélium defunctórum" in printed
    assert "defunctórum" not in digital
    doc = json.loads((CORPUS / "texts" / (tid.replace(".", "/", 1) + ".json")).read_text())
    words = doc["segments"][0]["words"]
    assert len(words) == 24
    assert [w["id"] for w in words[:6]] == ["w001", "w002", "w003", "w004", "w005", "w024"]
    assert words[3]["head"] == "w005"
    assert word(tid.replace(".", "/", 1), "w015")["morph"]["voice"] == "dep"


def test_requiem_epistle_preserves_the_chosen_print_reading_and_future_completion():
    from checks.collate import load_witness

    text = "proprium/commemoratio-omnium-fidelium-defunctorum-missa-i-epistola"
    directory = CORPUS / "witnesses" / text.replace("/", ".", 1)
    _, printed = load_witness(directory / "mr.txt")
    _, digital = load_witness(directory / "do.txt")
    assert "resurgémus" in printed
    assert "resurgámus" in digital
    assert word(text, "w008")["morph"]["tense"] == "fut"
    completion = word(text, "w046")["morph"]
    assert (completion["tense"], completion["mood"]) == ("futperf", "ind")
    assert word(text, "w045")["morph"]["case"] == "nom"
    assert word(text, "w017")["morph"]["case"] == "gen"
    for wid in ("w061", "w066"):
        assert word(text, wid)["morph"]["case"] == "voc"


@pytest.mark.parametrize("language", ["pl", "en"])
def test_requiem_epistle_keeps_the_scope_of_all_and_not_all(language):
    doc = json.loads(
        (
            CORPUS
            / "languages"
            / language
            / "texts/proprium"
            / "commemoratio-omnium-fidelium-defunctorum-missa-i-epistola.json"
        ).read_text()
    )
    translation = doc["segments"]["s01"]["translation"]
    if language == "pl":
        assert (
            "Wszyscy wprawdzie zmartwychwstaniemy, ale nie wszyscy będziemy przemienieni"
            in translation
        )
        assert "Nie wszyscy wprawdzie zaśniemy" not in translation
        assert doc["words"]["w027"]["gloss"] == "niezniszczalni"
    else:
        assert "we will indeed all rise, but we will not all be changed" in translation
        assert "when this mortal body has put on immortality" in translation
        assert doc["words"]["w076"]["gloss"] == "of sin"
    assert all(
        "explanation" in doc["words"][wid] for wid in ("w011", "w027", "w033", "w046", "w077")
    )


def test_annunciation_gradual_and_tract_have_separate_boundaries():
    directory = CORPUS / "texts/proprium"
    prefix = "annuntiatio-beatae-mariae-virginis-"
    gradual = json.loads((directory / (prefix + "graduale.json")).read_text())
    tract = json.loads((directory / (prefix + "tractus.json")).read_text())
    assert len(gradual["segments"][0]["words"]) == 24
    surviving = [w for s in tract["segments"] for w in s.get("words", [])]
    assert len(surviving) == 42
    assert surviving[0]["id"] == "w025"
    assert tract["ids"]["next"] == 67
    assert all(tract["ids"]["retired"][f"w{i:03d}"] == "s01" for i in range(1, 25))
    assert word("proprium/" + prefix + "tractus", "w057")["morph"] == {
        "pos": "pron",
        "case": "dat",
        "number": "sg",
    }


def test_paschal_communion_keeps_its_independent_printed_witness_and_partial_digital_body():
    from build_reader.store import load
    from checks.collate import collate, load_witness

    tid = "proprium.annuntiatio-beatae-mariae-virginis-tempore-paschali-communio"
    directory = CORPUS / "witnesses" / tid
    digital, do_body = load_witness(directory / "do.txt")
    _, lu_body = load_witness(directory / "lu.txt")
    assert digital["covers"] == "w001-w011"
    assert len(do_body.split()) == 11 and "Allel" not in do_body
    assert (
        lu_body
        == "Ecce vírgo concípiet, et páriet fílium: et vocábitur nómen éjus Emmánuel. Allelúia."
    )
    doc, _ = load(CORPUS, tid)
    errors, warnings, tally = collate(doc, directory)
    assert errors == []
    assert warnings == []
    assert tally["witnesses"] == 2 and tally["partial"] == 1


@pytest.mark.parametrize(
    "lemma,expected",
    [
        ("carmen", ["song", "poem"]),
        ("cursus", ["course", "passage", "running"]),
        ("ministerium", ["service", "ministry", "office"]),
        ("parabola", ["parable", "comparison"]),
        ("praeconium", ["proclamation", "praise"]),
        ("saturitas", ["fullness", "abundance", "satiety"]),
        ("testis", ["witness"]),
    ],
)
def test_lexical_cards_cover_the_attested_sacred_context_not_an_unrelated_homograph(
    lemma, expected
):
    entries = json.loads((CORPUS / "languages/en/lexicon.json").read_text())["entries"]
    assert entries[lemma]["senses"] == expected


def test_palm_tract_preserves_the_printed_looking_verb_not_a_digital_substitution():
    token = word("proprium/dominica-ii-passionis-tractus", "w100")
    assert (token["form"], token["lemma"]) == ("inspexérunt", "inspicio")
    assert token["morph"]["tense"] == "perf"


def test_lateran_gradual_locus_predicates_and_direct_address():
    text = "proprium/dedicatio-archibasilicae-sanctissimi-salvatoris-graduale"
    assert word(text, "w005")["head"] == "w001"
    predicate = word(text, "w009")
    assert predicate["head"] == "w001"
    assert not predicate.get("substantive")
    assert word(text, "w011")["morph"]["case"] == "voc"


def test_lateran_tract_does_not_repeat_the_gradual_and_preserves_retired_links():
    path = CORPUS / "texts/proprium/dedicatio-archibasilicae-sanctissimi-salvatoris-tractus.json"
    doc = json.loads(path.read_text())
    words = [w for s in doc["segments"] for w in s.get("words", [])]
    assert words[0]["id"] == "w020"
    assert [w["form"] for w in words[:4]] == ["Qui", "confídunt", "in", "Dómino"]
    assert len(words) == 32
    retired = {f"w{i:03d}" for i in range(1, 20)}
    assert not retired.intersection(w["id"] for w in words)
    assert all(doc["ids"]["retired"][wid] == "s01" for wid in retired)


def test_lateran_psalm_distinguishes_residence_and_possession():
    text = "proprium/dedicatio-archibasilicae-sanctissimi-salvatoris-tractus"
    assert word(text, "w020")["morph"]["number"] == "pl"
    assert word(text, "w031")["morph"]["number"] == "sg"
    assert word(text, "w033")["morph"]["governs"] == "abl"
    assert word(text, "w034")["morph"]["case"] == "abl"
    assert word(text, "w035")["morph"]["case"] == "nom"
    assert word(text, "w038")["morph"]["gender"] == "f"
    people = word(text, "w043")["morph"]
    assert (people["case"], people["number"]) == ("gen", "sg")
    possessive = word(text, "w044")
    assert possessive["lemma"] == "suus"
    assert possessive["head"] == "w043"
    assert possessive["morph"] == {"pos": "adj", "case": "gen", "gender": "m", "number": "sg"}


@pytest.mark.parametrize("language", ["pl", "en"])
def test_lateran_psalm_keeps_the_inhabitant_and_realizes_each_circuitu_once(language):
    path = CORPUS / "languages" / language / "texts/proprium"
    doc = json.loads(
        (path / "dedicatio-archibasilicae-sanctissimi-salvatoris-tractus.json").read_text()
    )
    assert doc["words"]["w031"]["gloss"] == ("kto" if language == "pl" else "whoever")
    assert doc["words"]["w032"]["gloss"] == ("mieszka" if language == "pl" else "dwells")
    groups = doc["segments"]["s01"]["alignments"]
    assert next(a for a in groups if a["words"] == ["w036", "w037"])["gloss"] == (
        "wokół" if language == "pl" else "round about"
    )
    assert next(a for a in groups if a["words"] == ["w045", "w046", "w047"])["gloss"] == (
        "odtąd" if language == "pl" else "from now on"
    )
    translation = doc["segments"]["s01"]["translation"]
    assert "Sinai" not in translation
    assert ("Jerozolimie" if language == "pl" else "Jerusalem") in translation


def test_asto_does_not_invent_an_unattested_supine():
    entries = json.loads((CORPUS / "lexicon/lemmata.json").read_text())["entries"]
    assert entries["asto"]["head"] == "asto, ástare, ástiti"


@pytest.mark.parametrize(
    "text,identifier",
    [
        ("proprium/sancti-ioachim-confessoris-evangelium", "w001"),
        ("proprium/commemoratio-omnium-fidelium-defunctorum-missa-i-sequentia", "w044"),
    ],
)
def test_liber_means_a_book_not_free(text, identifier):
    token = word(text, identifier)
    assert token["lemma"] == "liber_volumen"
    assert token["morph"]["pos"] == "noun"


@pytest.mark.parametrize(
    "identifier,case",
    [
        ("w003", "gen"),
        ("w008", "gen"),
        ("w009", "nom"),
        ("w011", "acc"),
        ("w015", "acc"),
        ("w016", "nom"),
        ("w021", "acc"),
        ("w038", "acc"),
        ("w039", "nom"),
    ],
)
def test_genealogy_distinguishes_generation_subject_and_object(identifier, case):
    token = word("proprium/sancti-ioachim-confessoris-evangelium", identifier)
    assert token["morph"]["case"] == case
    if identifier in {"w038", "w039"}:
        assert token["lemma"] == "Aram"


@pytest.mark.parametrize(
    "text,identifier,lemma,pos",
    [
        ("dominica-ii-post-epiphaniam-evangelium", "w008", "Cana", "noun"),
        ("dominica-infra-octavam-nativitatis-evangelium", "w058", "Anna", "noun"),
        ("sanctae-annae-matris-beatae-mariae-virginis-epistola", "w035", "linum", "noun"),
        ("dominica-x-post-pentecosten-introitus", "w024", "iacto", "verb"),
        ("dominica-in-septuagesima-epistola", "w049", "pugno", "verb"),
        ("dominica-i-passionis-epistola", "w077", "mediator", "noun"),
        ("dominica-vi-post-epiphaniam-evangelium", "w064", "satum", "noun"),
        ("dominica-xxiv-post-pentecosten-evangelium", "w066", "fuga", "noun"),
        ("nativitas-domini-in-die-epistola", "w171", "amictus", "noun"),
    ],
)
def test_context_selects_the_dictionary_identity(text, identifier, lemma, pos):
    token = word(f"proprium/{text}", identifier)
    assert (token["lemma"], token["morph"]["pos"]) == (lemma, pos)


@pytest.mark.parametrize(
    "text,identifier,lemma,pos",
    [
        ("dominica-i-in-quadragesima-evangelium", "w147", "vado", "verb"),
        ("dominica-iii-post-pentecosten-evangelium", "w052", "novem", "adj"),
        ("dominica-iii-post-pentecosten-evangelium", "w106", "novem", "adj"),
        ("dominica-xiii-post-pentecosten-evangelium", "w090", "novem", "adj"),
        ("dominica-iii-post-epiphaniam-evangelium", "w090", "venio", "verb"),
        ("vigilia-pentecostes-evangelium", "w058", "venio", "verb"),
        ("dominica-xxi-post-pentecosten-collecta", "w015", "liber", "adj"),
        ("sancti-lucae-evangelistae-secreta", "w007", "liber", "adj"),
        ("dominica-in-albis-evangelium", "w113", "fixura", "noun"),
        ("sancti-thomae-apostoli-evangelium", "w034", "fixura", "noun"),
        ("sanctorum-innocentium-martyrum-evangelium", "w080", "magus", "noun"),
        ("sanctorum-innocentium-martyrum-evangelium", "w107", "magus", "noun"),
    ],
)
def test_context_distinguishes_homonymous_forms(text, identifier, lemma, pos):
    token = word(f"proprium/{text}", identifier)
    assert (token["lemma"], token["morph"]["pos"]) == (lemma, pos)


def test_veniam_can_still_mean_forgiveness():
    token = word("proprium/sancti-matthiae-apostoli-postcommunio", "w016")
    assert token["lemma"] == "venia"
    assert token["morph"]["pos"] == "noun"


@pytest.mark.parametrize(
    "part,identifier",
    [
        ("introitus", "w003"),
        ("introitus", "w033"),
        ("graduale", "w003"),
        ("communio", "w016"),
        ("sequentia", "w207"),
    ],
)
def test_requiem_dona_is_a_command(part, identifier):
    token = word(f"proprium/commemoratio-omnium-fidelium-defunctorum-missa-i-{part}", identifier)
    assert token["lemma"] == "dono"
    assert (token["morph"]["pos"], token["morph"]["mood"], token["morph"]["person"]) == (
        "verb",
        "imp",
        2,
    )


def test_dona_can_still_mean_gifts():
    token = word("ordinarium/te-igitur", "w022")
    assert (token["lemma"], token["morph"]["pos"]) == ("donum", "noun")


@pytest.mark.parametrize(
    "identifier,case", [("w011", "acc"), ("w014", "voc"), ("w016", "abl"), ("w022", "abl")]
)
def test_requiem_psalm_distinguishes_object_address_and_place(identifier, case):
    token = word("proprium/commemoratio-omnium-fidelium-defunctorum-missa-i-introitus", identifier)
    assert token["morph"]["case"] == case


def test_david_is_a_witness_in_an_ablative_absolute():
    assert (
        word("proprium/commemoratio-omnium-fidelium-defunctorum-missa-i-sequentia", "w010")[
            "morph"
        ]["case"]
        == "abl"
    )


@pytest.mark.parametrize(
    "text,identifier,lemma,pos",
    [
        ("dominica-resurrectionis-evangelium", "w019", "mane", "adv"),
        ("dominica-ii-passionis-evangelium", "w655", "mane", "noun"),
        ("dominica-ii-passionis-evangelium", "w654", "amare_adverb", "adv"),
        ("dominica-in-albis-evangelium", "w005", "sero_adverb", "adv"),
        ("dominica-xix-post-pentecosten-evangelium", "w126", "egredior", "verb"),
        ("cathedra-sancti-petri-offertorium", "w016", "adversus_prep", "prep"),
        ("nativitas-domini-in-die-offertorium", "w014", "fundo_stabilio", "verb"),
        ("dominica-v-post-pascha-collecta", "w007", "largior", "verb"),
    ],
)
def test_context_distinguishes_morning_evening_and_verbal_homonyms(text, identifier, lemma, pos):
    token = word(f"proprium/{text}", identifier)
    assert (token["lemma"], token["morph"]["pos"]) == (lemma, pos)


@pytest.mark.parametrize(
    "text,identifier",
    [
        ("dominica-iv-post-pascha-introitus", "w001"),
        ("dominica-iv-post-pascha-introitus", "w048"),
        ("maternitas-beatae-mariae-virginis-introitus", "w012"),
        ("nativitas-domini-in-die-introitus", "w022"),
    ],
)
def test_cantate_addresses_multiple_singers(text, identifier):
    token = word(f"proprium/{text}", identifier)
    morph = token["morph"]
    assert (morph["mood"], morph["person"], morph["number"]) == ("imp", 2, "pl")
    assert "case" not in morph


def test_largire_is_a_deponent_command_not_an_infinitive():
    morph = word("proprium/dominica-v-post-pascha-collecta", "w007")["morph"]
    assert (morph["mood"], morph["voice"], morph["person"]) == ("imp", "dep", 2)


def test_genuine_vocative_participle_is_preserved():
    morph = word("litaniae/lauretanae", "w292")["morph"]
    assert (morph["mood"], morph["case"]) == ("part", "voc")


@pytest.mark.parametrize(
    "text,identifier",
    [
        ("annuntiatio-beatae-mariae-virginis-evangelium", "w063"),
        ("sancti-thomae-apostoli-evangelium", "w020"),
        ("feria-v-in-cena-domini-evangelium", "w048"),
    ],
)
def test_ei_is_the_recipient_not_a_plural_subject(text, identifier):
    token = word(f"proprium/{text}", identifier)
    assert token["morph"]["case"] == "dat"
    assert token["morph"]["number"] == "sg"


@pytest.mark.parametrize("identifier", ["w017", "w020"])
def test_easter_collect_has_active_gerunds(identifier):
    token = word("proprium/dominica-resurrectionis-collecta", identifier)
    assert (token["morph"]["mood"], token["morph"]["case"], token["morph"]["voice"]) == (
        "ger",
        "abl",
        "act",
    )


def test_thomas_gospel_retains_the_printed_imperative():
    token = word("proprium/sancti-thomae-apostoli-evangelium", "w080")
    assert (token["form"], token["lemma"], token["morph"]["mood"]) == ("Infer", "infero", "imp")


@pytest.mark.parametrize(
    "text,identifier",
    [
        ("orationes/memorare", "w001"),
        ("proprium/dominica-xvi-post-pentecosten-communio", "w002"),
    ],
)
def test_remember_is_the_deponent_verb_not_passive_recounting(text, identifier):
    token = word(text, identifier)
    assert (token["lemma"], token["morph"]["voice"]) == ("memoror", "dep")


def test_impersonal_perfect_infinitive_has_accusative_participle():
    token = word("orationes/memorare", "w008")
    assert (token["morph"]["case"], token["morph"]["gender"]) == ("acc", "n")


@pytest.mark.parametrize(
    "text,identifier,head,case,number,gender",
    [
        (
            "commemoratio-omnium-fidelium-defunctorum-missa-i-sequentia",
            "w020",
            "w018",
            "nom",
            "sg",
            "m",
        ),
        (
            "commemoratio-omnium-fidelium-defunctorum-missa-i-sequentia",
            "w023",
            "w018",
            "nom",
            "sg",
            "m",
        ),
        (
            "commemoratio-omnium-fidelium-defunctorum-missa-i-sequentia",
            "w043",
            "w041",
            "nom",
            "sg",
            "f",
        ),
        (
            "commemoratio-omnium-fidelium-defunctorum-missa-i-sequentia",
            "w068",
            "w065",
            "nom",
            "sg",
            "m",
        ),
        (
            "commemoratio-omnium-fidelium-defunctorum-missa-ii-epistola",
            "w031",
            "w028",
            "acc",
            "pl",
            "m",
        ),
        (
            "dedicatio-archibasilicae-sanctissimi-salvatoris-evangelium",
            "w048",
            "w047",
            "nom",
            "sg",
            "m",
        ),
        ("dominica-iv-in-quadragesima-evangelium", "w076", "w075", "nom", "sg", "m"),
        ("dominica-iv-in-quadragesima-evangelium", "w208", "w209", "nom", "pl", "m"),
        ("exaltatio-sanctae-crucis-evangelium", "w036", "w035", "nom", "sg", "m"),
        ("purificatio-beatae-mariae-virginis-communio", "w008", "w009", "acc", "sg", "m"),
        ("purificatio-beatae-mariae-virginis-evangelium", "w083", "w084", "acc", "sg", "m"),
        ("sancti-petri-et-pauli-apostolorum-epistola", "w069", "w072", "nom", "sg", "m"),
        ("vigilia-pentecostes-communio", "w023", "w025", "nom", "pl", "m"),
    ],
)
def test_future_participles_keep_their_expressed_subject(
    text, identifier, head, case, number, gender
):
    token = word(f"proprium/{text}", identifier)
    assert token.get("head") == head
    assert not token.get("substantive")
    assert tuple(token["morph"][k] for k in ("case", "number", "gender")) == (case, number, gender)


def test_venturi_can_still_modify_the_genitive_age_in_the_creed():
    token = word("ordinarium/credo", "w161")
    assert token["head"] == "w162"
    assert tuple(token["morph"][k] for k in ("case", "number", "gender")) == ("gen", "sg", "n")


@pytest.mark.parametrize("identifier", ["w006", "w018"])
def test_communion_addresses_god_directly(identifier):
    token = word("proprium/dominica-xvi-post-pentecosten-communio", identifier)
    assert token["morph"]["case"] == "voc"


def test_from_my_youth_has_an_ablative_possessive():
    token = word("proprium/dominica-xvi-post-pentecosten-communio", "w011")
    assert token.get("head") == "w010"
    assert token["morph"]["case"] == "abl"


@pytest.mark.parametrize(
    "text,language,segment,words,gloss",
    [
        ("orationes/memorare", "pl", "s01", ["w006", "w007", "w008"], "że nie słyszano"),
        ("orationes/memorare", "en", "s01", ["w006", "w007", "w008"], "that it has not been heard"),
        ("orationes/memorare", "pl", "s02", ["w022", "w023"], "został opuszczony"),
        ("orationes/memorare", "en", "s02", ["w022", "w023"], "was abandoned"),
        ("orationes/memorare", "en", "s01", ["w009", "w010"], "since time immemorial"),
        ("orationes/benedic-domine", "pl", "s03", ["w012", "w013"], "mamy spożywać"),
        ("proprium/dominica-ii-adventus-evangelium", "en", "s02", ["w021", "w022"], "art to come"),
        ("proprium/vigilia-pentecostes-communio", "en", "s01", ["w023", "w024"], "were to receive"),
    ],
)
def test_compound_realizations_preserve_the_finite_construction(
    text, language, segment, words, gloss
):
    path = CORPUS / "languages" / language / "texts" / f"{text}.json"
    layer = json.loads(path.read_text())
    matches = [a for a in layer["segments"][segment]["alignments"] if a["words"] == words]
    assert len(matches) == 1
    assert matches[0]["gloss"] == gloss
    assert all("gloss" not in layer["words"][wid] for wid in words)


@pytest.mark.parametrize(
    "text,identifiers",
    [
        ("cathedra-sancti-petri-collecta", ["w011", "w013"]),
        ("commemoratio-omnium-fidelium-defunctorum-missa-iii-evangelium", ["w050"]),
        ("dominica-ii-post-epiphaniam-epistola", ["w019", "w028"]),
        ("dominica-iii-post-epiphaniam-collecta", ["w010"]),
        ("dominica-in-septuagesima-postcommunio", ["w011", "w014"]),
        ("dominica-in-sexagesima-evangelium", ["w078"]),
        ("dominica-iv-post-pascha-epistola", ["w045", "w049"]),
        ("dominica-v-post-epiphaniam-evangelium", ["w116"]),
        ("dominica-viii-post-pentecosten-collecta", ["w007", "w013"]),
        ("dominica-x-post-pentecosten-collecta", ["w005", "w008"]),
        ("dominica-xii-post-pentecosten-evangelium", ["w049"]),
        ("dominica-xii-post-pentecosten-secreta", ["w013"]),
        ("dominica-xix-post-pentecosten-epistola", ["w056"]),
        ("dominica-xv-post-pentecosten-graduale", ["w011"]),
        ("dominica-xviii-post-pentecosten-evangelium", ["w082"]),
        ("feria-v-in-cena-domini-epistola", ["w018", "w032", "w034"]),
        ("immaculatum-cor-beatae-mariae-virginis-postcommunio", ["w017"]),
        ("nativitas-sancti-ioannis-baptistae-evangelium", ["w005"]),
        ("purificatio-beatae-mariae-virginis-epistola", ["w048"]),
        ("sancti-laurentii-martyris-epistola", ["w076"]),
        ("sanctorum-innocentium-martyrum-collecta", ["w009", "w011"]),
        ("sanctorum-innocentium-martyrum-evangelium", ["w037"]),
        ("sanctorum-simonis-et-iudae-apostolorum-collecta", ["w023", "w026"]),
        ("septem-dolorum-beatae-mariae-virginis-collecta", ["w026"]),
        ("septem-dolorum-beatae-mariae-virginis-sequentia", ["w077", "w100"]),
        ("vigilia-nativitatis-epistola", ["w056"]),
    ],
)
def test_contextual_verbal_nouns_are_not_passive_participles(text, identifiers):
    for identifier in identifiers:
        token = word(f"proprium/{text}", identifier)
        assert (token["morph"]["mood"], token["morph"]["voice"]) == ("ger", "act")
        assert "head" not in token


def test_agreeing_liberandum_remains_a_gerundive():
    token = word("orationes/te-deum", "w086")
    assert token["head"] == "w088"
    assert (token["morph"]["mood"], token["morph"]["voice"]) == ("part", "pass")


def test_the_gifts_are_to_be_received_not_the_sanctification():
    token = word("proprium/dominica-iii-post-pentecosten-secreta", "w011")
    assert token["head"] == "w003"
    assert tuple(token["morph"][k] for k in ("case", "number", "gender")) == ("acc", "pl", "n")


def test_judas_thinks_and_the_fallen_are_to_rise():
    text = "proprium/commemoratio-omnium-fidelium-defunctorum-missa-ii-epistola"
    assert word(text, "w025")["head"] == "w006"
    assert word(text, "w031")["head"] == "w028"
    for identifier in ("w029", "w045"):
        assert word(text, identifier)["morph"]["number"] == "pl"


def test_lexicon_does_not_invent_paradigm_forms():
    entries = json.loads((CORPUS / "lexicon/lemmata.json").read_text())["entries"]
    assert entries["duodecim"]["head"] == "duódecim"
    assert entries["saluber"]["head"] == "salúber, salúbris, salúbre"
    assert entries["Iudas"]["head"] == "Iudas, Iudæ"


def test_gloria_patri_has_a_nominative_but_cum_gloria_an_ablative():
    assert (
        word("proprium/sancti-matthaei-apostoli-et-evangelistae-introitus", "w026")["morph"]["case"]
        == "nom"
    )
    assert word("ordinarium/credo", "w106")["morph"]["case"] == "abl"


def layer(language, text):
    return json.loads((CORPUS / "languages" / language / "texts" / f"{text}.json").read_text())


@pytest.mark.parametrize("language,gloss", [("pl", "nieobłudnej"), ("en", "unfeigned")])
def test_non_ficta_is_not_a_double_negative(language, gloss):
    doc = layer(language, "proprium/dominica-i-in-quadragesima-epistola")
    alignment = next(a for a in doc["segments"]["s01"]["alignments"] if "w081" in a["words"])
    assert alignment["words"] == ["w081", "w082"]
    assert alignment["gloss"] == gloss
    assert all("gloss" not in doc["words"][wid] for wid in alignment["words"])


def test_sequence_translations_follow_their_own_latin_stanza():
    doc = layer("en", "proprium/commemoratio-omnium-fidelium-defunctorum-missa-i-sequentia")
    sheep = doc["segments"]["s15"]["translation"]
    accursed = doc["segments"]["s16"]["translation"]
    assert "Your sheep" in sheep and "Your right" in sheep
    assert "flames" not in sheep
    assert "the cursed" in accursed and "the blessed" in accursed
    assert "Your sheep" not in accursed


def test_postcommunion_conclusion_preserves_person_and_addressee():
    doc = layer("en", "proprium/pretiosissimi-sanguinis-domini-nostri-iesu-christi-postcommunio")
    target = doc["segments"]["s01"]["translation"]
    assert "Who liveth and reigneth with Thee" in target
    assert "Who livest" not in target


def test_creaturae_preserves_the_witnessed_genitive():
    token = word("proprium/d-n-iesu-christi-regis-epistola", "w045")
    assert token["form"] == "creatúræ"
    assert token["morph"]["case"] == "gen"


@pytest.mark.parametrize("identifier", ["w016", "w063", "w118", "w140", "w161"])
def test_pentecost_gospel_subjects_are_not_direct_addresses(identifier):
    token = word("proprium/dominica-pentecostes-evangelium", identifier)
    assert token["morph"]["case"] == "nom"


def test_genuine_address_to_the_father_remains_vocative():
    token = word("proprium/dominica-ii-passionis-evangelium", "w059")
    assert token["lemma"] == "pater"
    assert token["morph"]["case"] == "voc"


@pytest.mark.parametrize(
    "text,identifier",
    [
        ("dominica-iv-in-quadragesima-communio", "w014"),
        ("dominica-iv-in-quadragesima-communio", "w015"),
        ("dominica-xxiv-post-pentecosten-evangelium", "w215"),
    ],
)
def test_tribus_names_tribes_not_the_number_three(text, identifier):
    token = word(f"proprium/{text}", identifier)
    assert token["lemma"] == "tribus"
    assert token["morph"]["case"] == "nom"
    assert token["morph"]["number"] == "pl"


def test_three_measures_retains_the_numeral():
    token = word("proprium/dominica-vi-post-epiphaniam-evangelium", "w065")
    assert token["lemma"] == "tres"
    assert token["morph"]["case"] == "abl"


def test_pentecost_retains_the_printed_sermonem():
    token = word("proprium/dominica-pentecostes-evangelium", "w038")
    assert token["form"] == "sermónem"
    assert token["morph"]["case"] == "acc"


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("part", ["collecta", "secreta"])
def test_maundy_thursday_does_not_insert_an_unprinted_conclusion(language, part):
    target = layer(language, f"proprium/feria-v-in-cena-domini-{part}")
    text = target["segments"]["s01"]["translation"]
    assert "Przez Pana naszego" not in text
    assert "Through our Lord" not in text
    assert ("On z Tobą" if language == "pl" else "He liveth") in text


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize(
    "text,segment,ids",
    [
        ("dominica-i-adventus-introitus", "s01", ["w011", "w012"]),
        ("dominica-i-adventus-introitus", "s05", ["w065", "w066"]),
        ("dominica-i-adventus-offertorium", "s01", ["w012", "w013"]),
    ],
)
def test_non_erubescam_carries_one_negative_petition(language, text, segment, ids):
    target = layer(language, f"proprium/{text}")
    alignment = next(a for a in target["segments"][segment]["alignments"] if a["words"] == ids)
    expected = "niech nie będę zawstydzony" if language == "pl" else "let me not be put to shame"
    assert alignment["gloss"] == expected
    assert all("gloss" not in target["words"][wid] for wid in ids)


def test_palm_gradual_adjectives_modify_the_expressed_hand():
    text = "proprium/dominica-ii-passionis-graduale"
    right = word(text, "w003")
    assert right["lemma"] == "dexter"
    assert right["morph"] == {"pos": "adj", "case": "acc", "gender": "f", "number": "sg"}
    assert right["head"] == "w002"
    assert word(text, "w004")["head"] == "w002"


def test_palm_gradual_possessive_modifies_the_expressed_will():
    token = word("proprium/dominica-ii-passionis-graduale", "w008")
    assert token["head"] == "w007"
    assert "substantive" not in token


def test_easter_alleluia_has_a_right_hand_subject_not_an_instrument():
    token = word("proprium/dominica-iv-post-pascha-alleluia", "w007")
    assert token["lemma"] == "dextera"
    assert token["morph"]["case"] == "nom"


def test_easter_alleluia_death_will_not_rule_rather_than_be_ruled():
    token = word("proprium/dominica-iv-post-pascha-alleluia", "w023")
    assert token["lemma"] == "dominor"
    assert token["morph"]["voice"] == "dep"
    assert token["morph"]["tense"] == "fut"


def test_palm_gradual_follows_the_printed_spellings():
    from checks.collate import load_witness

    directory = CORPUS / "witnesses/proprium.dominica-ii-passionis-graduale"
    _, printed = load_witness(directory / "mr.txt")
    _, digital = load_witness(directory / "do.txt")
    assert "Israël" in printed and "Ísrael" not in printed
    assert printed.count("pene") == 2 and "pæne" not in printed
    assert digital.count("pæne") == 2
    # The reading text prints what page 138 prints: the diaeresis and the
    # spelling without the ligature. The digital spelling is a ruled variant.
    assert word("proprium/dominica-ii-passionis-graduale", "w018")["form"] == "Israël"
    apparatus = json.loads((directory / "apparatus.json").read_text())
    readings = {row["at"]: row for row in apparatus["adjudicated"]}
    for wid in ("w024", "w028"):
        assert word("proprium/dominica-ii-passionis-graduale", wid)["form"] == "pene"
        assert readings[wid]["witnesses"]["do"] == "pæne"
        assert readings[wid]["class"] == "orthography"


def test_easter_alleluia_records_the_printed_comma_and_digital_omission():
    from checks.collate import load_witness

    directory = CORPUS / "witnesses/proprium.dominica-iv-post-pascha-alleluia"
    _, printed = load_witness(directory / "mr.txt")
    _, digital = load_witness(directory / "do.txt")
    assert "mórtuis, iam" in printed and "mórtuis jam" in digital
    assert word("proprium/dominica-iv-post-pascha-alleluia", "w015")["post"] == ","
    apparatus = json.loads((directory / "apparatus.json").read_text())
    reading = next(row for row in apparatus["adjudicated"] if row["at"] == "w015")
    assert reading["ours"] == "mórtuis,"
    assert reading["witnesses"]["do"] == "mórtuis"


@pytest.mark.parametrize("language,sense", [("pl", "prawy"), ("en", "right-hand")])
def test_dexter_card_includes_the_spatial_adjective(language, sense):
    lexicon = json.loads((CORPUS / "languages" / language / "lexicon.json").read_text())
    assert lexicon["entries"]["dexter"]["senses"][0] == sense


def test_easter_alleluia_polish_continuous_text_preserves_future_dominion():
    target = layer("pl", "proprium/dominica-iv-post-pascha-alleluia")
    assert "śmierć nie będzie już nad Nim panować" in target["segments"]["s01"]["translation"]
    assert target["words"]["w023"]["gloss"] == "zapanuje"


@pytest.mark.parametrize(
    "text,identifier,case",
    [
        ("cathedra-sancti-petri-epistola", "w003", "gen"),
        ("dominica-ii-passionis-evangelium", "w260", "abl"),
        ("dominica-iv-post-epiphaniam-evangelium", "w005", "abl"),
        ("dominica-xxiii-post-pentecosten-evangelium", "w005", "abl"),
        ("sancti-ioannis-apostoli-et-evangelistae-evangelium", "w040", "dat"),
        ("sancti-thomae-apostoli-epistola", "w026", "abl"),
        ("sancta-familia-collecta", "w002", "voc"),
        ("sancti-stephani-protomartyris-epistola", "w128", "voc"),
    ],
)
def test_iesu_case_follows_its_clause_not_its_spelling(text, identifier, case):
    token = word(f"proprium/{text}", identifier)
    assert token["lemma"] == "Iesus"
    assert token["morph"]["case"] == case
    assert "decl" not in token["morph"]


@pytest.mark.parametrize(
    "text,identifier,head",
    [
        ("dominica-ii-passionis-evangelium", "w259", "w260"),
        ("dominica-vi-post-pentecosten-evangelium", "w008", "w009"),
    ],
)
def test_cum_iesu_expresses_accompaniment(text, identifier, head):
    token = word(f"proprium/{text}", identifier)
    assert token["morph"] == {"pos": "prep", "governs": "abl"}
    assert token["head"] == head
    assert word(f"proprium/{text}", head)["morph"]["case"] == "abl"


def test_sixth_sunday_keeps_the_other_cum_as_a_conjunction():
    assert word("proprium/dominica-vi-post-pentecosten-evangelium", "w004")["morph"] == {
        "pos": "conj"
    }


@pytest.mark.parametrize(
    "text,gloss",
    [
        ("dominica-iv-post-epiphaniam-evangelium", "when Jesus entered"),
        ("dominica-xxiii-post-pentecosten-evangelium", "while Jesus was speaking"),
    ],
)
def test_absolute_participle_has_its_subject_and_one_english_realization(text, gloss):
    token = word(f"proprium/{text}", "w004")
    assert token["head"] == "w005"
    assert "substantive" not in token
    target = layer("en", f"proprium/{text}")
    alignment = next(a for a in target["segments"]["s01"]["alignments"] if "w004" in a["words"])
    assert alignment == {"words": ["w004", "w005"], "anchor": "w004", "gloss": gloss}
    assert all("gloss" not in target["words"][wid] for wid in alignment["words"])


def test_john_polish_speech_verb_agrees_with_its_recipient():
    target = layer("pl", "proprium/sancti-ioannis-apostoli-et-evangelistae-evangelium")
    assert target["words"]["w039"]["gloss"] == "powiedział"
    assert target["words"]["w040"]["gloss"] == "Jezusowi"


@pytest.mark.parametrize(
    "language,gloss,explanation",
    [
        (
            "pl",
            "a głównym kamieniem węgielnym jest sam Chrystus Jezus",
            "W łacinie nie ma tu czasownika „być”",
        ),
        (
            "en",
            "with Christ Jesus Himself as the chief cornerstone",
            "Latin leaves the verb ‘to be’ unexpressed",
        ),
    ],
)
def test_thomas_nominal_absolute_is_translated_without_inventing_a_latin_verb(
    language, gloss, explanation
):
    text = "proprium/sancti-thomae-apostoli-epistola"
    target = layer(language, text)
    ids = [f"w{i:03}" for i in range(21, 27)]
    alignment = next(a for a in target["segments"]["s01"]["alignments"] if "w021" in a["words"])
    assert alignment == {"words": ids, "anchor": "w021", "gloss": gloss}
    assert all("gloss" not in target["words"][wid] for wid in ids)
    assert explanation in target["words"]["w021"]["explanation"]
    assert all(word(text, wid)["morph"]["pos"] != "verb" for wid in ids)
    core = json.loads((CORPUS / "texts" / f"{text}.json").read_text())
    assert core["localization"]["explanations"]["w021"] == {}


@pytest.mark.parametrize(
    "text,identifier",
    [
        ("cathedra-sancti-petri-epistola", "w040"),
        ("cathedra-sancti-petri-epistola", "w054"),
        ("dedicatio-sancti-michaelis-archangeli-epistola", "w025"),
        ("sacratissimi-cordis-iesu-epistola", "w075"),
    ],
)
def test_jesus_christ_name_chain_does_not_double_the_english_genitive(text, identifier):
    assert layer("en", f"proprium/{text}")["words"][identifier]["gloss"] == "Christ"


def test_joachim_beloved_modifies_the_son_not_the_mother():
    target = layer("en", "proprium/sancti-ioachim-confessoris-postcommunio")
    alignment = next(a for a in target["segments"]["s01"]["alignments"] if "w018" in a["words"])
    assert alignment == {
        "words": ["w018", "w019", "w020"],
        "anchor": "w019",
        "gloss": "of Thy beloved Son",
    }


def test_joseph_secret_restores_the_explicit_son_title():
    target = layer("en", "proprium/sancti-ioseph-sponsi-beatae-mariae-virginis-secreta")
    assert target["words"]["w014"]["gloss"] == "of the Mother"
    assert (
        "Spouse of the Mother of Your Son, Jesus Christ our Lord"
        in target["segments"]["s01"]["translation"]
    )


def test_anne_secret_nested_genitive_keeps_the_son_relation():
    target = layer("en", "proprium/sanctae-annae-matris-beatae-mariae-virginis-secreta")
    alignment = next(a for a in target["segments"]["s01"]["alignments"] if "w014" in a["words"])
    assert alignment == {"words": ["w014", "w015"], "anchor": "w014", "gloss": "of Your Son"}
    assert "gloss" not in target["words"]["w014"]
