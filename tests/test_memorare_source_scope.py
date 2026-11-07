"""The familiar Polish Memorare distinguishes a comparator from a wording basis."""

import copy
import json
from pathlib import Path

import pytest

from build_reader import bibliography, store
from build_reader.emit import Table, language_artifact
from checks import translation_provenance as provenance

CORPUS = Path(__file__).resolve().parents[1]
TEXT = "orationes.memorare"
EDITION = "edition.katechizm-religji-rzymsko-katolickiej-1925"
ITEM = "item.katechizm-religji-rzymsko-katolickiej-1925.sbc"
COMPARATOR = "use.pl.orationes.memorare.s01.katechizm1925-comparator"
EXACT_BASIS = "use.pl.41ba73a0a872e81199c5"
WITHDRAWN = {
    "s01": "use.pl.14a59b196a09e3dbb7ee",
    "s02": "use.pl.6bebfdb6aec6457203fa",
    "s03": "use.pl.e9e6936ab1acdf4a453c",
    "s04": "use.pl.f74d3c66a3a8e7763d95",
    "s05": "use.pl.064170cfc064134bd113",
}
TARGET_HASHES = {
    "s01": "4daa13999bd6de567a582f3ab16aa210c308757208ff65d2885f073e7c509550",
    "s02": "097f7a516172c0631f6a2c7f3c4530ba45d3595174e27736751017819d0e3576",
    "s03": "468dae611bb97e505dd0a59ef84ebd7e4a09c0f6b59e935588eef705914a2e19",
    "s04": "4ac905159fb45aeb4116647890d852a80abdd9307062dc171c31acc25cb91d19",
    "s05": "d4f321ee91e5a56ba9ea1ba3195a80e4d4a49ea08b8279c2d62c665612f2d490",
    "s06": "1a6d510178add2137eeec2c85814f91d933c72e6cade6677b90d75b34f22230e",
    "s07": "e5267cb5b365df8746dfdb33aac5eb15fb4c9f142e3dd2e7f053675b263f40d0",
}


def legacy_ref(segment: str) -> str:
    return f"languages/pl/texts/orationes/memorare.json#/segments/{segment}/translation_citations/0"


@pytest.fixture(scope="module")
def subject():
    doc, layers = store.load(CORPUS, TEXT)
    graph, languages = bibliography.load(CORPUS)
    ledger = json.loads((CORPUS / "languages/pl/translation-provenance.json").read_text())
    rows = {row["segment"]: row for row in ledger["sites"] if row["text"] == TEXT}
    return doc, layers["pl"], graph, languages, rows


def reader_rows(
    subject, graph: dict, languages: dict
) -> tuple[dict, bibliography.ReaderCitationProjection]:
    doc, layer, _, _, _ = subject
    projection = bibliography.ReaderCitationProjection(CORPUS, graph, languages)
    artifact = language_artifact(
        doc,
        layer,
        Table(),
        store.translation_relationships(CORPUS, "pl"),
        projection,
    )
    return {row["id"]: row for row in artifact["seg"]}, projection


def assert_translation_attribution(subject, graph: dict, languages: dict) -> None:
    rows, projection = reader_rows(subject, graph, languages)
    assert set(rows) == set(TARGET_HASHES)
    for segment in WITHDRAWN:
        assert "tc" not in rows[segment], f"{segment}: withdrawn attachment was emitted"
        assert "tb" not in rows[segment], f"{segment}: unsupported relationship was emitted"
        assert legacy_ref(segment) in projection.excluded
    assert rows["s06"]["tb"] == "exact"
    assert len(rows["s06"]["tc"]) == 1
    assert legacy_ref("s06") in projection.kept
    assert "tc" not in rows["s07"]
    assert "tb" not in rows["s07"]


def assert_source_scopes(graph: dict, languages: dict) -> None:
    projected = bibliography.public_text_evidence(graph, languages["pl"])
    text = next(record for record in projected["texts"] if record["id"] == TEXT)
    entries = {
        entry["id"]: (group, entry) for group in text["source_groups"] for entry in group["entries"]
    }
    assert set(entries) == {COMPARATOR, EXACT_BASIS}
    for use_id, role, segment in (
        (COMPARATOR, "historical_wording_comparator", "s01"),
        (EXACT_BASIS, "historical_wording_basis", "s06"),
    ):
        group, entry = entries[use_id]
        assert group["role"] == role
        assert group["edition"] == EDITION
        assert group["digital_item"] == ITEM
        assert entry["address"] == {"kind": "segment", "segment": segment}
    assert entries[EXACT_BASIS][0]["locator"]["printed"] == "druk. s. 156"
    assert entries[EXACT_BASIS][0]["locator"]["scan"] == "PDF s. 161"
    bases, texts = provenance.wording_bases(languages["pl"]["uses"], "pl")
    assert TEXT not in texts, "a whole-prayer basis would cover the unsettled segments"
    assert {site for site in bases if site.startswith(f"{TEXT}.")} == {f"{TEXT}.s06.pl"}


def test_polish_memorare_preserves_protected_words_and_honest_review_state(subject):
    doc, layer, _, _, rows = subject
    assert set(rows) == set(TARGET_HASHES)
    for segment in doc["segments"]:
        sid = segment["id"]
        row = rows[sid]
        assert row["familiar_core"] is True
        assert (
            provenance.canonical_hash(layer["segments"][sid]["translation"]) == (TARGET_HASHES[sid])
        )
        assert row["target_sha256"] == TARGET_HASHES[sid]
        assert row["source_sha256"] == provenance.canonical_hash(provenance.source_payload(segment))
        if sid in WITHDRAWN:
            assert row["origin"] == "working-unsettled"
            assert row["review"] == "working"
    assert rows["s06"]["origin"] == "traditional"
    assert rows["s06"]["review"] == "internally-reviewed"
    assert rows["s07"]["origin"] == "trivial"
    assert rows["s07"]["review"] == "internally-reviewed"


def test_polish_memorare_emits_no_withdrawn_legacy_attribution(subject):
    _, _, graph, languages, _ = subject
    uses = {use["id"]: use for use in languages["pl"]["uses"]}
    for segment, use_id in WITHDRAWN.items():
        assert uses[use_id]["decision"] == "REMOVE"
        assert uses[use_id]["legacy_refs"] == [legacy_ref(segment)]
    assert uses[COMPARATOR].get("legacy_refs", []) == []
    assert_translation_attribution(subject, graph, languages)


def test_polish_memorare_exposes_only_the_bounded_comparator_and_exact_basis(subject):
    _, _, graph, languages, _ = subject
    assert_source_scopes(graph, languages)


@pytest.mark.parametrize("segment", WITHDRAWN)
def test_reviving_each_withdrawn_attachment_is_visible_to_the_reader_check(subject, segment):
    _, _, graph, languages, _ = subject
    assert_translation_attribution(subject, graph, languages)
    changed = copy.deepcopy(languages)
    use = next(use for use in changed["pl"]["uses"] if use["id"] == WITHDRAWN[segment])
    use["decision"] = "RETAIN_WITH_CORRECTION"
    with pytest.raises(AssertionError, match=f"{segment}: withdrawn attachment was emitted"):
        assert_translation_attribution(subject, graph, changed)
    assert_translation_attribution(subject, graph, languages)


@pytest.mark.parametrize("mutation", ["promote-comparator", "whole-prayer-basis"])
def test_wording_scope_check_rejects_comparator_promotion_and_whole_prayer_basis(subject, mutation):
    _, _, graph, languages, _ = subject
    assert_source_scopes(graph, languages)
    changed = copy.deepcopy(languages)
    use_id = COMPARATOR if mutation == "promote-comparator" else EXACT_BASIS
    use = next(use for use in changed["pl"]["uses"] if use["id"] == use_id)
    if mutation == "promote-comparator":
        use["role"] = "historical_wording_basis"
    else:
        use["address"] = {"kind": "text", "text": TEXT}
    with pytest.raises(AssertionError):
        assert_source_scopes(graph, changed)
    assert_source_scopes(graph, languages)


@pytest.mark.parametrize("segment", WITHDRAWN)
def test_unsettled_memorare_cannot_inherit_an_internal_review(subject, monkeypatch, segment):
    doc, layer, _, _, rows = subject
    recorded = {row["site"]: copy.deepcopy(row) for row in rows.values()}
    # Run the real checker on this actual prayer, without accepting other texts
    # through a synthetic replacement ledger or a whole-book acceptance assertion.
    monkeypatch.setattr(store, "all_texts", lambda _corpus: [(doc, {"pl": layer})])
    monkeypatch.setattr(provenance, "load", lambda _corpus: (recorded, []))
    site = f"{TEXT}.{segment}.pl"
    assert recorded[site]["origin"] == "working-unsettled"
    assert provenance.check(CORPUS)[0] == []
    recorded[site]["review"] = "internally-reviewed"
    assert provenance.check(CORPUS)[0] == [
        f"{site}: unsettled origin cannot claim review=internally-reviewed"
    ]
    recorded[site]["review"] = "working"
    assert provenance.check(CORPUS)[0] == []
