"""Complete blessing layers stay aligned and current without snapshotting targets."""

import copy
import json
from pathlib import Path

import pytest

from build_reader import store
from checks.language_packs import check_core, check_layer
from checks.prose import check as check_prose
from checks.translation_provenance import REVIEWS, corpus_sites
from checks.translation_provenance import check as check_provenance

ROOT = Path(__file__).resolve().parents[2]
TEXT = "ordinarium.iube-domine-benedicere"
CORE = "texts/ordinarium/iube-domine-benedicere.json"
WORDS = [f"w{i:03}" for i in range(1, 21)]
PL_ABOUT = (
    "Przed Ewangelią Mszy kapłan, który odprawia bez diakona i subdiakona, "
    "po modlitwie „Munda cor meum” prosi Pana o błogosławieństwo dla siebie. "
    "We Mszy za zmarłych opuszcza tę prośbę i następującą po niej modlitwę."
)
TITLES = {
    "pl": "Prośba o błogosławieństwo przed Ewangelią",
    "en": "Prayer for a blessing before the Gospel",
}
GROUPS = {
    "s01": [(["w001", "w002", "w003"], "w001")],
    "s02": [(["w004", "w005"], "w005"), (["w007", "w008"], "w007"), (["w011", "w012"], "w011")],
    "s03": [],
}


def read(root, relative):
    return json.loads((root / relative).read_text(encoding="utf-8"))


def subject(language):
    return (
        store.core(ROOT, TEXT),
        store.raw_layer(ROOT, language, TEXT),
        store.layer_path(ROOT, language, TEXT),
    )


def assert_manifest(manifest, language):
    texts = manifest["texts"]
    assert texts.count(TEXT) == 1
    assert texts == [text for text in store.text_ids(ROOT) if text in set(texts)]
    assert manifest["titles"][TEXT]["title"] == TITLES[language]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_all_twenty_language_records_and_three_segments_have_real_help(language):
    core, layer, filename = subject(language)
    assert check_core(core) == []
    assert list(layer["words"]) == WORDS
    assert list(layer["segments"]) == ["s01", "s02", "s03"]
    assert check_layer(core, layer, filename) == []
    assert check_prose(layer) == []
    expected = copy.deepcopy(GROUPS)
    if language == "en":
        expected["s02"].append((["w014", "w015", "w016", "w017"], "w017"))
    expected["s02"].append((["w018", "w019"], "w018"))
    for sid, segment in layer["segments"].items():
        alignments = segment.get("alignments", [])
        assert [(entry["words"], entry.get("anchor")) for entry in alignments] == expected[sid]
        assert all(
            isinstance(entry.get("gloss"), str) and entry["gloss"].strip() and "reason" not in entry
            for entry in alignments
        )
        assert segment["translation"].strip()
    if language == "pl":
        assert layer["about"] == PL_ABOUT
    else:
        assert layer["about"].strip()


@pytest.mark.parametrize("language", ["pl", "en"])
def test_grouped_member_record_is_still_required_and_restored(language):
    core, layer, filename = subject(language)
    before = copy.deepcopy(layer)
    assert check_layer(core, layer, filename) == []
    assert "w002" in layer["words"] and "gloss" not in layer["words"]["w002"]
    del layer["words"]["w002"]
    assert any("word coverage or order" in error for error in check_layer(core, layer, filename))
    layer = before
    assert check_layer(core, layer, filename) == []


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize(
    "change,fragment",
    [
        ("duplicate", "words must be unique"),
        ("reverse", "contiguous and in source order"),
        ("anchor", "anchor must name the source word"),
        ("omit", "expected exactly one direct gloss or alignment"),
    ],
)
def test_real_first_group_rejects_corruption_then_restores(language, change, fragment):
    core, layer, filename = subject(language)
    before = copy.deepcopy(layer)
    assert check_layer(core, layer, filename) == []
    group = layer["segments"]["s01"]["alignments"][0]
    if change == "duplicate":
        group["words"].append("w003")
    elif change == "reverse":
        group["words"].reverse()
    elif change == "anchor":
        group["anchor"] = "w020"
    else:
        layer["segments"]["s01"]["alignments"] = []
    assert any(fragment in error for error in check_layer(core, layer, filename))
    layer = before
    assert check_layer(core, layer, filename) == []


def test_missing_latest_polish_about_rejects_then_restores():
    core, layer, filename = subject("pl")
    before = layer.pop("about")
    assert before == PL_ABOUT
    assert any("about is required" in error for error in check_layer(core, layer, filename))
    layer["about"] = before
    assert check_layer(core, layer, filename) == []


@pytest.mark.parametrize("language", ["pl", "en"])
def test_new_manifest_identity_title_and_position_reject_displacement(language):
    manifest = read(ROOT, f"languages/{language}/manifest.json")
    assert_manifest(manifest, language)
    original = copy.deepcopy(manifest)
    manifest["texts"] = [text for text in manifest["texts"] if text != TEXT] + [TEXT]
    with pytest.raises(AssertionError):
        assert_manifest(manifest, language)
    manifest = original
    assert_manifest(manifest, language)


def test_new_adverb_and_all_reused_lemma_links_are_real_not_complete_card_snapshots():
    core = store.core(ROOT, TEXT)
    neutral = read(ROOT, "lexicon/lemmata.json")["entries"]
    words = [word for segment in core["segments"] for word in segment["words"]]
    assert len({word["lemma"] for word in words}) == 16
    assert neutral["competenter"]["head"] == "competénter"
    assert neutral["competenter"]["pos"] == "adv"
    assert next(word for word in words if word["id"] == "w016")["lemma"] == "competenter"
    for language in ("pl", "en"):
        entries = read(ROOT, f"languages/{language}/lexicon.json")["entries"]
        for word in words:
            assert neutral[word["lemma"]]["head"].strip()
            assert all(
                isinstance(sense, str) and sense.strip()
                for sense in entries[word["lemma"]]["senses"]
            )
            assert entries[word["lemma"]]["senses"]


def test_six_actual_provenance_sites_bind_current_source_and_target_without_permanent_review_pin(
    blessing_corpus,
):
    root = blessing_corpus
    errors, tally = check_provenance(root)
    assert errors == [] and sum(tally.values()) == 6
    current = corpus_sites(root)
    assert set(current) == {
        f"{TEXT}.{sid}.{language}" for sid in ("s01", "s02", "s03") for language in ("pl", "en")
    }
    for language in ("pl", "en"):
        rows = read(root, f"languages/{language}/translation-provenance.json")["sites"]
        assert len(rows) == 3 and {row["segment"] for row in rows} == {"s01", "s02", "s03"}
        for row in rows:
            actual = current[row["site"]]
            assert row["review"] in REVIEWS
            assert row["source_sha256"] == actual["source_sha256"]
            assert row["target_sha256"] == actual["target_sha256"]
            assert row["familiar_core"] == actual["familiar_core"]
    # Working/internally/expert-reviewed are distinct legal states, not new approvals.


@pytest.mark.parametrize("change", ["source", "target-pl", "target-en"])
def test_real_source_or_target_edit_stales_exact_provenance_sites_then_restores(
    blessing_corpus, change
):
    root = blessing_corpus
    assert check_provenance(root)[0] == []
    if change == "source":
        path = root / CORE
    else:
        path = root / "languages" / change.removeprefix("target-") / CORE
    before = path.read_bytes()
    data = json.loads(before)
    if change == "source":
        assert data["segments"][1]["words"][4]["id"] == "w008"
        del data["segments"][1]["words"][4]["post"]
        expected = {f"{TEXT}.s02.{language}: stale source_sha256" for language in ("pl", "en")}
    else:
        data["segments"]["s02"]["translation"] += " Test change."
        expected = {f"{TEXT}.s02.{change.removeprefix('target-')}: stale target_sha256"}
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    try:
        assert set(check_provenance(root)[0]) == expected
    finally:
        path.write_bytes(before)
    assert path.read_bytes() == before
    assert check_provenance(root)[0] == []


@pytest.mark.parametrize("language", ["pl", "en"])
def test_unfounded_inherited_origin_rejects_then_restores(blessing_corpus, language):
    root = blessing_corpus
    assert check_provenance(root)[0] == []
    assert corpus_sites(root)[f"{TEXT}.s01.{language}"]["has_wording_citations"] is False
    path = root / "languages" / language / "translation-provenance.json"
    before = path.read_bytes()
    data = json.loads(before)
    next(row for row in data["sites"] if row["segment"] == "s01")["origin"] = "public-domain"
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    try:
        assert check_provenance(root)[0] == [
            f"{TEXT}.s01.{language}: origin=public-domain requires a wording citation"
        ]
    finally:
        path.write_bytes(before)
    assert check_provenance(root)[0] == []
