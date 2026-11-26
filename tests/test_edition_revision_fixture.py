"""Edition predecessors have exact snapshots and separately scoped frame views.

Current product validation keeps live inputs. These helpers exist only for the
historical assertions that deliberately compare an earlier accepted edition.
"""

import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pytest
from edition_revision_fixture import (
    BIBLIOGRAPHY_FILES,
    CAPTION_FILES,
    COMMUNION_FILES,
    FILES,
    GRATIA_FILES,
    LAYER_CHANGES,
    OWNER_FILES,
    PUBLISHED_FILES,
    PUBLISHED_LAYER_CHANGES,
    READING_FILES,
    REVIEW_FILES,
    RUBRIC_CAPTION_FILES,
    SOURCE_SCOPE_FILES,
    WITNESS_FILES,
    before_bibliography_record,
    before_bibliography_revision,
    before_bibliography_subject,
    before_communion_revision,
    before_edition_layer,
    before_edition_object,
    before_edition_revision,
    before_edition_target_row,
    before_reading_revision,
    current_bibliography_record,
    current_bibliography_review,
    current_edition_caption,
    current_edition_target_sha,
    current_edition_value,
)

from build_reader.bibliography_bindings import (
    _SourceSnapshot,
    _witness_subject,
    digest,
    text_document,
)
from checks.translation_provenance import canonical_hash

ROOT = Path(__file__).resolve().parents[1]
TRANSLATIONS = [
    (relative, change)
    for relative, changes in LAYER_CHANGES.items()
    for change in changes
    if change["path"][0] == "segments"
    and change["path"][-1] == "translation"
    and "before" in change
    and "after" in change
]


def at(value, fields):
    for field in fields:
        value = value[field]
    return value


def test_scope_is_nonempty_and_names_each_declared_subject_once():
    assert len(PUBLISHED_FILES) == 144
    assert len(PUBLISHED_LAYER_CHANGES) == 128
    assert len(CAPTION_FILES) == 72
    assert len(REVIEW_FILES) == 48
    assert len(OWNER_FILES) == 33
    assert len(WITNESS_FILES) == 6
    assert not any("changes" in entry for entry in WITNESS_FILES.values())
    assert len(SOURCE_SCOPE_FILES) == 12
    assert len(RUBRIC_CAPTION_FILES) == 169
    non_layer_files = {
        relative for relative, entry in RUBRIC_CAPTION_FILES.items() if not entry.get("changes")
    }
    assert non_layer_files == {
        "bibliography/graph.json",
        "languages/en/bibliography.json",
        "languages/en/lexicon.json",
        "languages/en/translation-basis.json",
        "languages/pl/lexicon.json",
        "languages/en/translation-provenance.json",
        "languages/pl/translation-provenance.json",
        "texts/ordinarium/evangelium-ultimum.json",
        "texts/ordinarium/iudica-me.json",
        "texts/ordinarium/supplices-te-rogamus.json",
        "texts/ordinarium/suscipe-sancta-trinitas.json",
        "texts/ordinarium/te-igitur.json",
        "texts/proprium/commemoratio-omnium-fidelium-defunctorum-missa-i-offertorium.json",
        "texts/proprium/corporis-christi-alleluia.json",
        "texts/proprium/corporis-christi-evangelium.json",
        "texts/proprium/dominica-ii-adventus-epistola.json",
        "texts/proprium/dominica-iii-post-pentecosten-graduale.json",
        "texts/proprium/dominica-iv-post-pascha-introitus.json",
        "texts/proprium/dominica-x-post-pentecosten-introitus.json",
        "texts/proprium/nativitas-beatae-mariae-virginis-epistola.json",
        "texts/proprium/pretiosissimi-sanguinis-domini-nostri-iesu-christi-communio.json",
        "texts/proprium/pretiosissimi-sanguinis-domini-nostri-iesu-christi-secreta.json",
        "texts/proprium/vigilia-nativitatis-epistola.json",
        "texts/psalmi/118-he.json",
    }
    assert sum(len(entry.get("changes", ())) for entry in RUBRIC_CAPTION_FILES.values()) == 281
    assert len(READING_FILES) == 1723
    assert len(COMMUNION_FILES) == 12
    previous = set().union(
        PUBLISHED_FILES,
        CAPTION_FILES,
        REVIEW_FILES,
        OWNER_FILES,
        WITNESS_FILES,
        SOURCE_SCOPE_FILES,
        RUBRIC_CAPTION_FILES,
        READING_FILES,
        COMMUNION_FILES,
    )
    assert len(previous) == 1901
    assert set(GRATIA_FILES) == {
        f"languages/{lang}/texts/orationes/ave-maria.json" for lang in ("pl", "en")
    }
    assert set(FILES) == previous | BIBLIOGRAPHY_FILES.keys() | GRATIA_FILES.keys()
    assert len(LAYER_CHANGES) == 1857
    assert len(TRANSLATIONS) == 234
    assert set(LAYER_CHANGES) <= set(FILES)
    for relative, changes in LAYER_CHANGES.items():
        assert relative.startswith("languages/") and "/texts/" in relative
        assert len(changes) == len({tuple(change["path"]) for change in changes})
        assert all(change.get("before") != change.get("after") for change in changes)


@pytest.mark.parametrize("relative", sorted(READING_FILES))
def test_reading_revision_restores_its_exact_published_input(relative):
    raw = before_communion_revision(relative, (ROOT / relative).read_bytes())
    previous = before_reading_revision(relative, raw)
    entry = READING_FILES[relative]
    assert hashlib.sha256(raw).hexdigest() == entry["current"]
    assert hashlib.sha256(previous).hexdigest() == entry["previous"]
    assert before_reading_revision(relative, previous) is previous
    damaged = raw + b" "
    assert before_reading_revision(relative, damaged) is damaged


@pytest.mark.parametrize("relative", sorted(BIBLIOGRAPHY_FILES))
def test_bibliographic_revision_restores_the_original_and_rejects_a_changed_input(relative):
    entry = BIBLIOGRAPHY_FILES[relative]
    raw = (ROOT / relative).read_bytes()
    previous = before_bibliography_revision(relative, raw)
    assert hashlib.sha256(raw).hexdigest() == entry["current"]
    assert hashlib.sha256(previous).hexdigest() == entry["previous"]
    assert before_bibliography_revision(relative, previous) is previous
    damaged = raw + b" "
    assert before_bibliography_revision(relative, damaged) is damaged


def test_bibliographic_review_predecessor_requires_the_complete_witness_and_its_sources():
    graph = json.loads((ROOT / "bibliography/graph.json").read_bytes())
    text = "proprium.nativitas-domini-in-aurora-secreta"
    identity = f"witness.{text}.do44667ff"
    witness = next(w for w in graph["witnesses"] if w["id"] == identity)
    original = before_bibliography_record("witnesses", witness)
    assert original["review"] != witness["review"]
    assert current_bibliography_record("witnesses", original) == witness
    missing = {k: v for k, v in witness.items() if k != "review"}
    assert before_bibliography_record("witnesses", missing) is missing
    assert current_bibliography_review(identity, "0" * 64) == "0" * 64
    assert current_bibliography_review(identity, None) is None
    current = _witness_subject(
        ROOT, witness, text_document(ROOT, text), _SourceSnapshot(ROOT, graph), reviewable=True
    )
    previous = before_bibliography_subject(current, reviewable=True)
    assert digest(current) == witness["review"]["sha256"]
    assert digest(previous) == original["review"]["sha256"]
    changed = deepcopy(current)
    use = changed["source_uses"][witness["use"]]["use"]
    use["locator"]["passages"][1]["url"] = "https://example.org/another-book#L90"
    assert before_bibliography_subject(changed, reviewable=True) is changed
    previous["source_uses"].clear()
    original["review"].clear()
    assert digest(before_bibliography_subject(current, reviewable=True)) != digest(previous)
    assert before_bibliography_record("witnesses", witness)["review"]["status"] == "reviewed"


@pytest.mark.parametrize("relative", sorted(COMMUNION_FILES))
def test_communion_revision_restores_only_the_exact_preceding_file(relative):
    raw = before_bibliography_revision(relative, (ROOT / relative).read_bytes())
    entry = COMMUNION_FILES[relative]
    previous = before_communion_revision(relative, raw)
    assert hashlib.sha256(raw).hexdigest() == entry["current"]
    assert hashlib.sha256(previous).hexdigest() == entry["previous"]
    assert before_communion_revision(relative, previous) is previous
    damaged = raw + b" "
    assert before_communion_revision(relative, damaged) is damaged


@pytest.mark.parametrize("relative", sorted(FILES))
def test_complete_current_bytes_reach_exact_predecessor_without_modifying_source(relative):
    raw = (ROOT / relative).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == FILES[relative]["current"]
    old = before_edition_revision(relative, raw)
    assert old != raw
    assert hashlib.sha256(old).hexdigest() == FILES[relative]["previous"]
    assert before_edition_revision(relative, old) is old
    damaged = raw + b" "
    assert before_edition_revision(relative, damaged) is damaged
    assert (ROOT / relative).read_bytes() == raw


@pytest.mark.parametrize("relative", sorted(path for path in FILES if path.endswith(".json")))
def test_complete_object_projection_is_exact_and_keeps_unknown_fields_for_old_guards(relative):
    raw = (ROOT / relative).read_bytes()
    current = json.loads(raw)
    saved = deepcopy(current)
    previous = before_edition_object(relative, current)
    assert previous == json.loads(before_edition_revision(relative, raw))
    assert previous != current and current == saved
    assert before_edition_object(relative, previous) is previous
    if isinstance(current, dict):
        current["unknown_historical_comparison_field"] = {"fault": True}
    else:
        current.append("unknown historical comparison entry")
    damaged = deepcopy(current)
    assert before_edition_object(relative, current) is current
    assert current == damaged
    assert (ROOT / relative).read_bytes() == raw


@pytest.mark.parametrize("relative", sorted(LAYER_CHANGES))
def test_layer_frame_restores_enrolled_fields_and_preserves_unlisted_faults(relative):
    layer = json.loads((ROOT / relative).read_bytes())
    saved = deepcopy(layer)
    expected = json.loads(before_edition_revision(relative, (ROOT / relative).read_bytes()))
    assert before_edition_layer(layer) == expected
    assert layer == saved
    layer["unlisted_comparison_fault"] = {"exact": ["preserve", "this"]}
    damaged = deepcopy(layer)
    result = before_edition_layer(layer)
    assert result == {**expected, "unlisted_comparison_fault": {"exact": ["preserve", "this"]}}
    assert layer == damaged
    # A declared field with a different value must not be silently repaired.
    fields = LAYER_CHANGES[relative][0]["path"]
    parent = at(layer, fields[:-1])
    parent[fields[-1]] = {"unrecognized": "changed enrolled field"}
    damaged = deepcopy(layer)
    result = before_edition_layer(layer)
    assert at(result, fields) == {"unrecognized": "changed enrolled field"}
    assert layer == damaged


@pytest.mark.parametrize("relative,change", TRANSLATIONS, ids=lambda item: str(item)[:70])
def test_live_expected_values_advance_only_the_exact_declared_predecessor(relative, change):
    fields = change["path"]
    assert current_edition_value(relative, fields, change["before"]) == change["after"]
    assert current_edition_value(relative, fields, change["after"]) is change["after"]
    arbitrary = "A different unreviewed translation."
    assert current_edition_value(relative, fields, arbitrary) is arbitrary
    assert current_edition_value(relative, [*fields, "wrong"], change["before"]) is change["before"]
    parts = relative.split("/")
    language, text, segment = parts[1], parts[3] + "." + Path(parts[4]).stem, fields[1]
    old_sha, new_sha = canonical_hash(change["before"]), canonical_hash(change["after"])
    assert current_edition_target_sha(text, language, segment, old_sha) == new_sha
    assert current_edition_target_sha(text, language, segment, "0" * 64) == "0" * 64
    row = {
        "text": text,
        "language": language,
        "segment": segment,
        "target_sha256": new_sha,
        "source_sha256": "unrelated source field",
        "origin": "unrelated origin",
        "extra_comparison_fault": {"must": "survive"},
    }
    saved = deepcopy(row)
    assert before_edition_target_row(row) == {**row, "target_sha256": old_sha}
    assert row == saved
    row["target_sha256"] = "0" * 64
    assert before_edition_target_row(row) is row


def test_unknown_inputs_are_identity_preserving_and_do_not_gain_a_predecessor():
    raw = b'{"unlisted": true}\n'
    obj = {"unlisted": True}
    assert before_edition_revision("not-a-listed-subject.json", raw) is raw
    assert before_edition_object("not-a-listed-subject.json", obj) is obj
    assert before_edition_layer(obj) is obj
    assert current_edition_value("not-a-listed-subject.json", ["unlisted"], True) is True


@pytest.mark.parametrize(
    "text,segment,words,previous,expected",
    [
        (
            "orationes.pater-noster",
            "s02",
            ("w009",),
            "Your",
            {"words": ["w008", "w009"], "anchor": "w008", "gloss": "Your name"},
        ),
        (
            "orationes.angelus-domini",
            "s05",
            ("w048",),
            "your",
            {"words": ["w047", "w048"], "anchor": "w047", "gloss": "your word"},
        ),
        (
            "proprium.sancti-ioseph-sponsi-beatae-mariae-virginis-collecta",
            "s01",
            ("w001", "w002", "w003"),
            "Of Your Most Holy Mother",
            {
                "words": ["w001", "w002", "w003"],
                "anchor": "w002",
                "gloss": "Of Your most holy Mother",
            },
        ),
        (
            "proprium.sancti-stephani-protomartyris-secreta",
            "s01",
            ("w005", "w006", "w007"),
            "memory of Your Saints",
            {"words": ["w005", "w006", "w007"], "anchor": "w006", "gloss": "memory of Your saints"},
        ),
    ],
)
def test_current_caption_expectations_bind_only_exact_declared_old_spans(
    text, segment, words, previous, expected
):
    result = current_edition_caption("en", text, segment, words, previous)
    assert result == expected
    relative = f"languages/en/texts/{text.replace('.', '/', 1)}.json"
    current = json.loads((ROOT / relative).read_bytes())
    assert expected in current["segments"][segment]["alignments"]
    assert current_edition_caption("en", text, segment, words, previous + " Changed") is None
    assert current_edition_caption("en", text, segment, ("w999",), previous) is None
    assert current_edition_caption("en", text, "missing-segment", words, previous) is None
    assert current_edition_caption("xx", text, segment, words, previous) is None
    assert current_edition_caption("en", text, segment, (), previous) is None
    result["words"].append("unlisted fault")
    result["gloss"] = "Unreviewed caption"
    assert current_edition_caption("en", text, segment, words, previous) == expected
