"""Third Sunday source extents and grammatical caption relations."""

import copy
import json
from pathlib import Path

import pytest

from checks import attribute
from checks.interlinear import check as providers
from checks.language_packs import check_layer
from checks.raw_binding import REGISTRY, BindingError, resolve_binding
from checks.transcription import check_transcriptions

ROOT = Path(__file__).resolve().parents[1]
P = "proprium.dominica-iii-post-epiphaniam-"
KEY = "do-proprium-dominica-iii-post-epiphaniam-alleluia"


def load(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def documents(slug, language):
    rel = "texts/proprium/dominica-iii-post-epiphaniam-" + slug + ".json"
    return load(rel), load("languages/" + language + "/" + rel)


def group(layer, first, last, caption):
    ids = [f"w{n:03}" for n in range(first, last + 1)]
    found = [
        g
        for s in layer["segments"].values()
        for g in s.get("alignments", [])
        if set(g["words"]) & set(ids)
    ]
    assert found == [{"words": ids, "anchor": ids[0], "gloss": caption}]
    assert all("gloss" not in layer["words"][w] for w in ids)


@pytest.mark.parametrize(
    "slug,language,first,last,caption",
    [
        ("epistola", "pl", 35, 37, "Nie mścijcie się sami"),
        ("epistola", "en", 35, 37, "Do not avenge yourselves"),
        ("epistola", "en", 7, 11, "repay no one evil for evil"),
        ("evangelium", "en", 9, 13, "great multitudes followed Him"),
        ("evangelium", "en", 38, 41, "his leprosy was cleansed"),
        ("evangelium", "pl", 38, 41, "został oczyszczony z trądu"),
        ("evangelium", "en", 46, 48, "See that you tell no one"),
        ("evangelium", "en", 112, 114, "my servant will be healed"),
        ("evangelium", "en", 145, 149, "On hearing this, however, Jesus marveled"),
        ("evangelium", "en", 205, 206, "let it be done for you"),
        ("evangelium", "en", 208, 210, "the servant was healed"),
        ("evangelium", "pl", 109, 110, "powiedz słowo"),
        ("secreta", "pl", 12, 16, "niech uświęci ciała i umysły poddanych Tobie"),
        ("secreta", "en", 12, 16, "sanctify the bodies and minds of those subject to You"),
    ],
)
def test_captions_preserve_agents_objects_and_government(slug, language, first, last, caption):
    core, layer = documents(slug, language)
    assert not providers(core, layer)
    path = (
        ROOT
        / "languages"
        / language
        / "texts/proprium"
        / ("dominica-iii-post-epiphaniam-" + slug + ".json")
    )
    assert not check_layer(core, layer, path)
    group(layer, first, last, caption)


@pytest.mark.parametrize("mutation", ["member", "anchor", "caption", "duplicate", "scalar"])
def test_caption_regression_guard_is_not_vacuous(mutation):
    _, layer = documents("evangelium", "en")
    expected = "my servant will be healed"
    group(layer, 112, 114, expected)
    selected = next(g for g in layer["segments"]["s01"]["alignments"] if g["words"][0] == "w112")
    if mutation == "member":
        selected["words"].pop()
    elif mutation == "anchor":
        selected["anchor"] = "w114"
    elif mutation == "caption":
        selected["gloss"] = "my servant will heal"
    elif mutation == "duplicate":
        layer["segments"]["s01"]["alignments"].append(copy.deepcopy(selected))
    else:
        layer["words"]["w114"]["gloss"] = "will heal"
    with pytest.raises(AssertionError):
        group(layer, 112, 114, expected)


@pytest.mark.parametrize(
    "slug,word",
    [
        ("epistola", "w037"),
        ("evangelium", "w026"),
        ("evangelium", "w035"),
        ("evangelium", "w040"),
        ("evangelium", "w110"),
    ],
)
@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("mutation", ["missing-note", "missing-declaration"])
def test_local_grammar_notes_have_both_language_layers(slug, word, language, mutation):
    core, layer = documents(slug, language)
    path = (
        ROOT
        / "languages"
        / language
        / "texts/proprium"
        / ("dominica-iii-post-epiphaniam-" + slug + ".json")
    )
    assert word in core["localization"]["explanations"]
    assert layer["words"][word]["explanation"]
    assert not check_layer(core, layer, path)
    if mutation == "missing-note":
        del layer["words"][word]["explanation"]
    else:
        del core["localization"]["explanations"][word]
    assert check_layer(core, layer, path)


def test_latin_forms_and_contextual_analysis_are_not_changed_by_english():
    epistle, pl = documents("epistola", "pl")
    words = {w["id"]: w for s in epistle["segments"] for w in s["words"]}
    assert words["w037"]["morph"]["mood"] == "part"
    assert words["w037"]["morph"]["voice"] == "act"
    assert "ogólnego zakazu obrony" in pl["words"]["w037"]["explanation"]
    gospel, en = documents("evangelium", "en")
    words = {w["id"]: w for s in gospel["segments"] for w in s["words"]}
    assert words["w026"]["morph"]["mood"] == "inf" and words["w026"]["morph"]["voice"] == "act"
    assert words["w035"]["morph"]["mood"] == "imp" and words["w035"]["morph"]["voice"] == "pass"
    assert words["w038"]["morph"]["gender"] == "f"
    assert words["w038"]["morph"]["case"] == "nom"
    assert words["w040"]["morph"]["case"] == "nom"
    assert words["w110"]["morph"]["case"] == "abl"
    assert en["words"]["w034"]["gloss"] == "I am willing"
    assert en["words"]["w089"]["gloss"] == "I" and en["words"]["w090"]["gloss"] == "will come"
    assert words["w132"]["post"] == ":"
    assert "et vadit:" in (ROOT / "witnesses" / (P + "evangelium") / "mr.txt").read_text()
    assert "et vadit;" in (ROOT / "witnesses" / (P + "evangelium") / "do.txt").read_text()
    pc, _ = documents("postcommunio", "en")
    analysis = pc["editorial"]["words"]["w009"]["analysis"]
    assert analysis == {
        "confidence": "medium",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }


@pytest.mark.parametrize("slug,body", [("collecta", 15), ("secreta", 16), ("postcommunio", 14)])
def test_expanded_oration_is_a_declared_composite_not_full_proper_page(slug, body):
    graph = load("bibliography/graph.json")
    text = P + slug
    witness = next(w for w in graph["witnesses"] if w["id"] == "witness." + text + ".mr1962")
    assert witness["orthography_profile"] == "exact-declared-composite"
    assert witness["review"] == {"status": "pending"}
    for suffix in (
        "conclusion-rg115a",
        "conclusion-middle",
        "conclusion-terminal",
        "oration-boundaries",
    ):
        assert "use." + text + "." + suffix + ".mr1962" in witness["source_dependencies"]["uses"]
    raw = (ROOT / "witnesses" / text / "mr.txt").read_text()
    assert f"{body} body words" in raw and "Deus. Per ómnia" in raw
    assert "not direct proof" in raw


def alleluia_fixture(root):
    registry = load(REGISTRY)
    selected = registry["bindings"][KEY]
    archives = {k: registry["archives"][k] for k in {r["archive"] for r in selected["evidence"]}}
    data = {"version": registry["version"], "archives": archives, "bindings": {KEY: selected}}
    for archive in archives.values():
        target = root / archive["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((ROOT / archive["path"]).read_bytes())
    witness = root / selected["witness"]
    witness.parent.mkdir(parents=True, exist_ok=True)
    witness.write_bytes((ROOT / selected["witness"]).read_bytes())
    path = root / REGISTRY
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False))
    return witness, data


def test_alleluia_suffix_excludes_gradual_and_does_not_borrow_its_marker(tmp_path, monkeypatch):
    witness, _ = alleluia_fixture(tmp_path)
    result = resolve_binding(witness, tmp_path)
    assert (
        result.text
        == "Allelúja, allelúja. Dóminus regnávit, exsúltet terra: læténtur ínsulæ multæ. Allelúja."
    )
    assert result.fragments[0].start == 67 and result.fragments[0].end == 86
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    assert attribute.marked_lines(P + "alleluia") == []
    assert check_transcriptions(witness.parent) == ([], 1)


def test_coherent_gradual_extension_reaches_body_equality(tmp_path):
    witness, data = alleluia_fixture(tmp_path)
    assert resolve_binding(witness, tmp_path)
    selected = data["bindings"][KEY]
    evidence = selected["evidence"][0]
    archive = tmp_path / data["archives"][evidence["archive"]]["path"]
    line = archive.read_text().splitlines()[31]
    evidence["fragment"].update(start=0, text=line)
    selected["reading"][0]["fragment"]["start"] = 0
    witness.write_text(witness.read_text().replace("chars 67:86", "chars 0:86"))
    (tmp_path / REGISTRY).write_text(json.dumps(data, ensure_ascii=False))
    with pytest.raises(
        BindingError, match="transcription differs from its exact ordered raw reading"
    ):
        resolve_binding(witness, tmp_path)


def test_printed_fieri_and_selected_house_accent_are_distinct():
    core, _ = documents("epistola", "en")
    word = next(w for s in core["segments"] for w in s["words"] if w["id"] == "w024")
    assert word["form"] == "fíeri"
    assert "fieri" in (ROOT / "witnesses" / (P + "epistola") / "mr.txt").read_text()
    entries = load("witnesses/" + P + "epistola/apparatus.json")["adjudicated"]
    assert any(
        e["at"] == "w024"
        and e["ours"] == "fíeri"
        and e["witnesses"].get("mr") == "fieri"
        and e["class"] == "accent"
        for e in entries
    )


def test_introit_doxology_is_expanded_without_modernizing_protected_prose():
    graph = load("bibliography/graph.json")
    record = next(w for w in graph["witnesses"] if w["id"] == "witness." + P + "introitus.mr1962")
    assert record["orthography_profile"] == "exact-declared-composite"
    assert "use." + P + "introitus.doxology.mr1962" in record["source_dependencies"]["uses"]
    _, layer = documents("introitus", "en")
    assert (
        "Glory be to the Father, and to the Son, and to the Holy Ghost."
        in layer["segments"]["s01"]["translation"]
    )
    assert "world without end. Amen." in layer["segments"]["s01"]["translation"]


def junction_group(layer, ids, anchor, caption):
    found = [
        g
        for s in layer["segments"].values()
        for g in s.get("alignments", [])
        if set(g["words"]) & set(ids)
    ]
    assert found == [{"words": ids, "anchor": anchor, "gloss": caption}]
    assert all("gloss" not in layer["words"][w] for w in ids)


JUNCTIONS = [
    ("pl", ["w046", "w047"], "w047", "Do Mnie należy pomsta"),
    ("pl", ["w070", "w071", "w072"], "w071", "na jego głowę"),
    ("en", ["w005", "w006"], "w006", "in your own estimation"),
    ("en", ["w012", "w013"], "w012", "take care to do what is good"),
]


@pytest.mark.parametrize("language,ids,anchor,caption", JUNCTIONS)
@pytest.mark.parametrize("mutation", ["member", "anchor", "caption", "duplicate", "scalar"])
def test_epistle_junctions_and_healthy_first_controls(language, ids, anchor, caption, mutation):
    core, layer = documents("epistola", language)
    assert not providers(core, layer)
    junction_group(layer, ids, anchor, caption)
    changed = copy.deepcopy(layer)
    selected = next(g for g in changed["segments"]["s01"]["alignments"] if g["words"] == ids)
    if mutation == "member":
        selected["words"].pop()
    elif mutation == "anchor":
        selected["anchor"] = next(w for w in ids if w != anchor)
    elif mutation == "caption":
        selected["gloss"] = "provide possessions" if language == "en" else "nad jego głową"
    elif mutation == "duplicate":
        changed["segments"]["s01"]["alignments"].append(copy.deepcopy(selected))
    else:
        changed["words"][ids[0]]["gloss"] = "redundant"
    with pytest.raises(AssertionError):
        junction_group(changed, ids, anchor, caption)


def faith_caption(layer):
    assert layer["words"]["w159"]["gloss"] == "such great"
    assert layer["words"]["w160"]["gloss"] == "faith"
    assert not any(
        set(g["words"]) & {"w159", "w160"} for g in layer["segments"]["s01"]["alignments"]
    )
    assert "I have not found such great faith in Israel." in layer["segments"]["s01"]["translation"]


@pytest.mark.parametrize("mutation", ["old-scalar", "lost-noun", "old-prose"])
def test_gospel_degree_preserves_faith_and_complete_prose(mutation):
    core, layer = documents("evangelium", "en")
    assert not providers(core, layer)
    faith_caption(layer)
    changed = copy.deepcopy(layer)
    if mutation == "old-scalar":
        changed["words"]["w159"]["gloss"] = "so great"
    elif mutation == "lost-noun":
        changed["words"]["w160"]["gloss"] = "trustworthiness"
    else:
        changed["segments"]["s01"]["translation"] = changed["segments"]["s01"][
            "translation"
        ].replace("such great faith", "so great faith")
    with pytest.raises(AssertionError):
        faith_caption(changed)


def conduct_prose(layer):
    prose = layer["segments"]["s01"]["translation"]
    assert "Do not be wise in your own estimation." in prose
    assert (
        "Repay no one evil for evil; take care to do what is good "
        "not only before God but also before all men."
    ) in prose
    assert "provide good things" not in prose


@pytest.mark.parametrize("mutation", ["goods", "conceits", "omit-God", "omit-men"])
def test_epistle_conduct_prose_keeps_both_spheres(mutation):
    _, layer = documents("epistola", "en")
    conduct_prose(layer)
    changed = copy.deepcopy(layer)
    a, b = {
        "goods": ("take care to do what is good", "provide good things"),
        "conceits": ("in your own estimation", "in your own conceits"),
        "omit-God": ("not only before God but also ", ""),
        "omit-men": (" but also before all men", ""),
    }[mutation]
    changed["segments"]["s01"]["translation"] = changed["segments"]["s01"]["translation"].replace(
        a, b
    )
    with pytest.raises(AssertionError):
        conduct_prose(changed)


SOURCE_REASONS = {
    "collecta": (
        "The proper page contains the Collect and its short conclusion cue; "
        "the expanded conclusion and response come from the separately identified sources."
    ),
    "epistola": (
        "The full Epistle is printed on this page; "
        "the declared house accent on fíeri differs from the printed fieri."
    ),
    "evangelium": (
        "The full Gospel is printed on this page; the selected punctuation "
        "and the resumed printing’s accidental variants are declared separately."
    ),
    "introitus": (
        "The proper page abbreviates the doxology and antiphon repetition; "
        "the full doxology and repetition rule come from the separately identified sources."
    ),
    "postcommunio": (
        "The proper page contains the Postcommunion and its short conclusion cue; "
        "the expanded conclusion and response come from the separately identified sources."
    ),
    "secreta": (
        "The proper page contains the Secret and its short conclusion cue; "
        "the expanded conclusion and response come from the separately identified sources."
    ),
}


@pytest.mark.parametrize("slug,expected", list(SOURCE_REASONS.items()))
def test_source_reasons_state_coverage_not_review_process(slug, expected):
    graph = load("bibliography/graph.json")
    selected = next(r for r in graph["uses"] if r["id"] == "use." + P + slug + ".mr1962")
    assert selected["decision_reason"] == expected
    changed = copy.deepcopy(selected)
    changed["decision_reason"] = (
        "Actual body/cue boundary checked; corrects complete-single-page claim "
        "without source-review promotion."
    )
    with pytest.raises(AssertionError):
        assert changed["decision_reason"] == expected


def test_third_sunday_source_prose_has_readable_numbers_and_titles():
    graph = load("bibliography/graph.json")
    rows = [r for r in graph["uses"] if r["id"].startswith("use." + P)]
    strings = [
        s
        for r in rows
        for s in (
            r.get("claim", ""),
            r.get("decision_reason", ""),
            r.get("locator", {}).get("section", ""),
        )
    ]
    for bad in (
        "complete81-word",
        "complete213-word",
        "full20-word",
        "prints21",
        "AdventI",
        "DominicaIII",
        "p.45",
        "p.46",
        "RG115a",
        "RG427",
    ):
        assert all(bad not in s for s in strings)
    by_id = {r["id"]: r for r in rows}
    ep = by_id["use." + P + "epistola.mr1962"]
    go = by_id["use." + P + "evangelium.mr1962"]
    assert "p. 45 prints the complete 81-word Epistle" in ep["claim"]
    assert "p. 46 prints the complete 213-word Gospel" in go["claim"]
    assert ep["locator"]["printed"] == "p. 45" and go["locator"]["printed"] == "p. 46"
