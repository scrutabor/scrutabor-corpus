"""The Immaculate Heart Collect keeps its proper conclusion and literal witnesses."""

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import bibliography
from build_reader.bibliography_bindings import (
    digest,
    selected_text,
    transcript_digest,
    validate_bindings,
)
from checks import language_packs, syntax, translation_provenance
from checks.apparatus import derived_summary
from checks.collate import collate
from checks.raw_binding import REGISTRY, BindingError, resolve_binding

CORPUS = Path(__file__).resolve().parents[1]
TEXT = "proprium.immaculatum-cor-beatae-mariae-virginis-collecta"
CORE = "texts/proprium/immaculatum-cor-beatae-mariae-virginis-collecta.json"
BINDING = "do-proprium-immaculatum-cor-beatae-mariae-virginis-collecta"
LEGACY_WORDS = "30717b5ac991f1ffb63695e3f176a7d77d61a96f7bb5ddc3c40342b00ffa386a"
SEGMENT_STRUCTURE = "4869dcaa354f837a75f01bb27fd9e583088837f73b7fb3c66fd8743d8b19e7eb"
NEW_WORD = {
    "id": "w052",
    "form": "eiúsdem",
    "lemma": "idem",
    "morph": {"pos": "pron", "case": "gen", "number": "sg", "gender": "m"},
}
TRANSLATIONS = {
    "pl": (
        "Wszechmogący, wieczny Boże, który w Sercu błogosławionej Maryi Dziewicy "
        "przygotowałeś godne mieszkanie Ducha Świętego, łaskawie spraw, abyśmy zdołali "
        "żyć według Twojego serca, z pobożnym umysłem wspominając święto tegoż "
        "Niepokalanego Serca. Przez Pana naszego Jezusa Chrystusa, Syna Twojego, "
        "który z Tobą żyje i króluje w jedności tegoż Ducha Świętego, Bóg, na wieki wieków."
    ),
    "en": (
        "Almighty, everlasting God, Who in the Heart of the Blessed Virgin Mary "
        "prepared a dwelling place worthy of the Holy Spirit; graciously grant that "
        "we, who are devoutly keeping the feast of her Immaculate Heart, may be able "
        "to live according to Your Heart. Through our Lord Jesus Christ, Your Son, "
        "who lives and reigns with You in the unity of the same Holy Spirit, God, "
        "forever and ever."
    ),
}
DO_BODY = (
    "Omnípotens sempitérne Deus, qui in Corde beátæ Maríæ Vírginis dignum Spíritus "
    "Sancti habitáculum præparásti: concéde propítius; ut ejúsdem immaculáti Cordis "
    "festivitátem devóta mente recoléntes, secúndum cor tuum vívere valeámus. Per "
    "Dóminum nostrum Jesum Christum, Fílium tuum: qui tecum vivit et regnat in unitáte "
    "Spíritus Sancti Deus, per ómnia sǽcula sæculórum. Amen."
)
CONCLUSION_SOURCES = {
    "formula": (
        "direct_approved_print",
        "leaf n22 / PDF p. 23",
        "b511f3aa4016b387d2995b5089e15aa62593c04118052ef48dcc09352fcf769c",
    ),
    "prefix": (
        "direct_approved_print",
        "leaf n202 / PDF p. 203",
        "38c3d082c3cf4e7f82f87cf9f87595e62e3765cb625c1305005f1435cc985774",
    ),
    "terminal": (
        "direct_approved_print",
        "leaf n305 / PDF p. 306",
        "c8a123467dd47ace390100a021fdcdd61752a5c42635583b92d72cd636027f58",
    ),
    "variants": (
        "rubric_control",
        "leaf n23 / PDF p. 24",
        "db99d725287dbdb233ff9c22c94cd027ec6b5105f2f64817ec828778805ff132",
    ),
}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def words(doc):
    return [word for segment in doc["segments"] for word in segment.get("words", [])]


def body(path):
    return " ".join(
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    )


def historical_word_records(doc):
    """Reverse only the exact later contextual adjective on a checked copy."""
    expected = {
        "id": "w022",
        "form": "devóta",
        "lemma": "devotus",
        "morph": {"pos": "adj", "case": "abl", "gender": "f", "number": "sg"},
        "head": "w023",
    }
    sequence = deepcopy(words(doc))
    (selected,) = [word for word in sequence if word["id"] == "w022"]
    assert selected == expected, "contextual adjective"
    assert doc["editorial"]["words"]["w022"] == {
        "analysis": {
            "confidence": "high",
            "sources": ["editorial", "whitakers", "collatinus"],
            "review": "pending",
        }
    }, "pending adjective analysis"
    selected["lemma"] = "devoveo"
    selected["morph"] = {
        "pos": "verb",
        "case": "abl",
        "gender": "f",
        "number": "sg",
        "tense": "perf",
        "voice": "pass",
        "mood": "part",
        "conj": 2,
    }
    return sequence


def assert_prayer(doc):
    sequence = words(doc)
    expected = [f"w{n:03d}" for n in range(1, 44)]
    expected += ["w052", *[f"w{n:03d}" for n in range(44, 52)]]
    assert [word["id"] for word in sequence] == expected
    assert doc["ids"]["next"] == 53
    assert sequence[43] == NEW_WORD
    # Retain the original 51-record pin after the exact annotation-only inverse.
    historical = historical_word_records(doc)
    assert digest([word for word in historical if word["id"] != "w052"]) == LEGACY_WORDS
    assert (
        digest(
            [
                {key: value for key, value in segment.items() if key != "words"}
                for segment in doc["segments"]
            ]
        )
        == SEGMENT_STRUCTURE
    )
    assert [word["id"] for word in doc["segments"][1]["words"]] == ["w051"]


def assert_target(doc, layer, language):
    assert list(layer["words"]) == [word["id"] for word in words(doc)]
    assert layer["segments"]["s01"]["translation"] == TRANSLATIONS[language]
    assert layer["segments"]["s02"]["translation"] == "Amen."
    if language == "pl":
        assert layer["words"]["w052"] == {"gloss": "tegoż"}
    else:
        assert layer["words"]["w052"] == {}
        assert layer["segments"]["s01"]["alignments"] == [
            {"words": ["w011", "w012"], "anchor": "w011", "gloss": "of the Holy Spirit"},
            {
                "words": ["w052", "w044", "w045"],
                "anchor": "w044",
                "gloss": "of the same Holy Spirit",
            },
        ]


@pytest.fixture
def prayer(tmp_path):
    """Copy one actual prayer and its two raw dependencies; never rebind evidence."""
    root = tmp_path / "corpus"
    for relative in (
        CORE,
        f"witnesses/{TEXT}/mr.txt",
        f"witnesses/{TEXT}/do.txt",
        f"witnesses/{TEXT}/apparatus.json",
    ):
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CORPUS / relative, destination)
    graph = read(CORPUS / "bibliography/graph.json")
    graph["witnesses"] = [w for w in graph["witnesses"] if w["text"] == TEXT]
    graph["collations"] = [c for c in graph["collations"] if c["text"] == TEXT]
    graph["uses"] = [u for u in graph["uses"] if u.get("address", {}).get("text") == TEXT]
    write(root / "bibliography/graph.json", graph)
    registry = read(CORPUS / REGISTRY)
    binding = registry["bindings"][BINDING]
    archive_ids = {span["archive"] for span in binding["evidence"]}
    registry["archives"] = {key: registry["archives"][key] for key in archive_ids}
    registry["bindings"] = {BINDING: binding}
    write(root / REGISTRY, registry)
    for archive in registry["archives"].values():
        destination = root / archive["path"]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(CORPUS / archive["path"], destination)
    for language in ("pl", "en"):
        relative = f"languages/{language}/{CORE}"
        write(root / relative, read(CORPUS / relative))
        manifest = read(CORPUS / f"languages/{language}/manifest.json")
        manifest["texts"] = [TEXT]
        write(root / f"languages/{language}/manifest.json", manifest)
        write(
            root / f"languages/{language}/bibliography.json",
            {"schema_version": bibliography.SCHEMA, "language": language, "uses": []},
        )
        ledger = read(CORPUS / f"languages/{language}/translation-provenance.json")
        ledger["sites"] = [site for site in ledger["sites"] if site["text"] == TEXT]
        write(root / f"languages/{language}/translation-provenance.json", ledger)
    return root, graph


def test_stable_word_insertion_and_existing_prayer_are_exact(prayer):
    root, _ = prayer
    doc = read(root / CORE)
    saved = deepcopy(doc)
    assert_prayer(doc)
    for damage in ("old-lemma", "old-participle", "promoted-review", "lost-confirmation"):
        changed = deepcopy(doc)
        selected = next(word for word in words(changed) if word["id"] == "w022")
        if damage == "old-lemma":
            selected["lemma"] = "devoveo"
        elif damage == "old-participle":
            selected["morph"].update({"pos": "verb", "mood": "part"})
        elif damage == "promoted-review":
            changed["editorial"]["words"]["w022"]["analysis"]["review"] = "accepted"
        else:
            changed["editorial"]["words"]["w022"]["analysis"]["sources"] = ["editorial"]
        assert changed != saved, "annotation mutation changes its copy"
        with pytest.raises(AssertionError):
            assert_prayer(changed)
        changed.clear()
        changed.update(deepcopy(saved))
        assert_prayer(changed)
        assert changed == saved
    assert doc == saved


@pytest.mark.parametrize("change", ["delete", "renumber", "move", "gender", "old-body"])
def test_stable_word_contract_rejects_regressions(prayer, change):
    root, _ = prayer
    doc = read(root / CORE)
    sequence = doc["segments"][0]["words"]
    if change == "delete":
        sequence.pop(43)
    elif change == "renumber":
        sequence[43]["id"] = "w053"
    elif change == "move":
        sequence.insert(45, sequence.pop(43))
    elif change == "gender":
        sequence[43]["morph"]["gender"] = "n"
    else:
        sequence[0]["form"] = "Omnipotens"
    with pytest.raises(AssertionError):
        assert_prayer(doc)


@pytest.mark.parametrize("language", ["pl", "en"])
def test_full_target_and_word_gloss_are_exact(prayer, language):
    root, _ = prayer
    assert_target(read(root / CORE), read(root / f"languages/{language}/{CORE}"), language)


@pytest.mark.parametrize("change", ["pl-gloss", "pl-prose", "en-group", "en-prose"])
def test_target_contract_rejects_lost_same_reference(prayer, change):
    root, _ = prayer
    language = change[:2]
    layer = read(root / f"languages/{language}/{CORE}")
    segment = layer["segments"]["s01"]
    if change == "pl-gloss":
        layer["words"]["w052"]["gloss"] = "jego"
    elif change == "pl-prose":
        segment["translation"] = segment["translation"].replace(
            "jedności tegoż Ducha", "jedności Ducha"
        )
    elif change == "en-group":
        segment["alignments"][1]["words"].remove("w052")
    else:
        segment["translation"] = segment["translation"].replace(
            "of the same Holy Spirit", "of the Holy Spirit"
        )
    with pytest.raises(AssertionError):
        assert_target(read(root / CORE), layer, language)


def test_literal_digital51_and_composite_print52_collate(prayer):
    root, _ = prayer
    directory = root / "witnesses" / TEXT
    doc = read(root / CORE)
    assert body(directory / "do.txt") == DO_BODY
    assert len(body(directory / "do.txt").split()) == 51
    selected = " ".join(w.get("pre", "") + w["form"] + w.get("post", "") for w in words(doc))
    assert body(directory / "mr.txt") == selected
    assert len(selected.split()) == 52
    bound = resolve_binding(directory / "do.txt", root)
    assert bound is not None and bound.text == DO_BODY
    errors, _, stats = collate(doc, directory)
    assert errors == []
    assert stats["witnesses"] == 2 and stats["words"] == 52
    assert stats["omissions"] == 1
    apparatus = read(directory / "apparatus.json")
    omission = [entry for entry in apparatus["adjudicated"] if entry["class"] == "omission"]
    assert len(omission) == 1
    assert {key: omission[0][key] for key in ("at", "ours", "witnesses")} == {
        "at": "w052",
        "ours": "eiúsdem",
        "witnesses": {"do": ""},
    }
    assert apparatus["summary"] == derived_summary(apparatus)


@pytest.mark.parametrize("change", ["unruled", "no-positive-witness"])
def test_omission_requires_both_a_ruling_and_positive_witness(prayer, change):
    root, _ = prayer
    directory = root / "witnesses" / TEXT
    apparatus = read(directory / "apparatus.json")
    if change == "unruled":
        apparatus["adjudicated"] = [e for e in apparatus["adjudicated"] if e["class"] != "omission"]
    else:
        path = directory / "mr.txt"
        path.write_text(
            path.read_text().replace("in unitáte eiúsdem Spíritus", "in unitáte Spíritus")
        )
        next(e for e in apparatus["adjudicated"] if e["class"] == "omission")["witnesses"]["mr"] = (
            ""
        )
    apparatus["summary"] = derived_summary(apparatus)
    write(directory / "apparatus.json", apparatus)
    errors, _, _ = collate(read(root / CORE), directory)
    assert errors
    expected = "length mismatch" if change == "unruled" else "positive full-witness"
    assert any(expected in error for error in errors)


def test_digital_witness_cannot_be_silently_changed_to_the_print_reading(prayer):
    root, _ = prayer
    path = root / "witnesses" / TEXT / "do.txt"
    original = path.read_text()
    changed = original.replace("in unitáte Spíritus", "in unitáte ejúsdem Spíritus")
    assert changed != original
    path.write_text(changed)
    with pytest.raises(BindingError):
        resolve_binding(path, root)


def test_complete_conclusion_sources_and_current_hashes_are_bound(prayer):
    root, graph = prayer
    assert validate_bindings(root, graph) == []
    uses = {use["id"]: use for use in graph["uses"]}
    primary = uses[f"use.{TEXT}.mr1962"]
    assert primary["role"] == "direct_approved_print"
    assert primary["locator"]["scan"] == "leaf n728 / PDF p. 729"
    witness = next(w for w in graph["witnesses"] if w["transcription"] == "mr")
    required = {f"use.{TEXT}.conclusion-{name}.mr1962" for name in CONCLUSION_SOURCES}
    assert set(witness["source_dependencies"]["uses"]) == required
    assert len(witness["source_dependencies"]["uses"]) == len(required)
    assert witness["source_dependencies"]["raw_binding"] is None
    for name, (role, scan, evidence) in CONCLUSION_SOURCES.items():
        use = uses[f"use.{TEXT}.conclusion-{name}.mr1962"]
        assert (use["role"], use["locator"]["scan"], use["evidence_sha256"]) == (
            role,
            scan,
            evidence,
        )
    for record in graph["witnesses"]:
        path = root / "witnesses" / TEXT / f"{record['transcription']}.txt"
        assert record["transcription_sha256"] == transcript_digest(path.read_text())
    (collation,) = graph["collations"]
    assert collation["selected_text_sha256"] == digest(selected_text(read(root / CORE)))
    assert collation["apparatus_sha256"] == digest(
        read(root / "witnesses" / TEXT / "apparatus.json")
    )


@pytest.mark.parametrize("field", ["transcript", "selected", "apparatus", "source-role"])
def test_source_binding_rejects_stale_or_incompatible_claims(prayer, field):
    root, graph = prayer
    if field == "transcript":
        next(w for w in graph["witnesses"] if w["transcription"] == "mr")[
            "transcription_sha256"
        ] = "0" * 64
        expected = "transcription_sha256"
    elif field == "selected":
        graph["collations"][0]["selected_text_sha256"] = "0" * 64
        expected = "selected_text_sha256"
    elif field == "apparatus":
        graph["collations"][0]["apparatus_sha256"] = "0" * 64
        expected = "apparatus_sha256"
    else:
        next(u for u in graph["uses"] if u["id"] == f"use.{TEXT}.conclusion-variants.mr1962")[
            "role"
        ] = "historical_semantic_comparator"
        expected = "incompatible role"
    assert any(expected in error for error in validate_bindings(root, graph))


def test_both_language_provenance_sites_bind_current_source_and_target(prayer):
    root, _ = prayer
    errors, _ = translation_provenance.check(root)
    assert errors == []
    doc = read(root / CORE)
    for language in ("pl", "en"):
        ledger = read(root / f"languages/{language}/translation-provenance.json")
        layer = read(root / f"languages/{language}/{CORE}")
        assert len(ledger["sites"]) == 2
        for site in ledger["sites"]:
            segment = next(s for s in doc["segments"] if s["id"] == site["segment"])
            assert site["source_sha256"] == translation_provenance.canonical_hash(
                translation_provenance.source_payload(segment)
            )
            assert site["target_sha256"] == translation_provenance.canonical_hash(
                layer["segments"][site["segment"]]["translation"]
            )


@pytest.mark.parametrize("change", ["source", "pl-target", "en-target"])
def test_provenance_rejects_changed_source_or_target_without_rebinding(prayer, change):
    root, _ = prayer
    if change == "source":
        doc = read(root / CORE)
        next(w for w in words(doc) if w["id"] == "w052")["form"] = "eiusdem"
        write(root / CORE, doc)
        expected = {f"{TEXT}.s01.{language}: stale source_sha256" for language in ("pl", "en")}
    else:
        language = change[:2]
        path = root / f"languages/{language}/{CORE}"
        layer = read(path)
        layer["segments"]["s01"]["translation"] += " Changed."
        write(path, layer)
        expected = {f"{TEXT}.s01.{language}: stale target_sha256"}
    errors, _ = translation_provenance.check(root)
    assert expected <= set(errors)


def test_actual_syntax_and_language_consumers_accept_the_prayer(prayer):
    root, _ = prayer
    doc = read(root / CORE)
    assert syntax.check(doc) == []
    for language in ("pl", "en"):
        path = root / f"languages/{language}/{CORE}"
        assert language_packs.check_layer(doc, read(path), path) == []


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("change", ["append", "swap", "delete"])
def test_actual_layer_consumer_rejects_wrong_word_coverage_or_order(prayer, language, change):
    root, _ = prayer
    doc = read(root / CORE)
    path = root / f"languages/{language}/{CORE}"
    layer = read(path)
    original_entries = dict(layer["words"])
    if change == "append":
        layer["words"]["w052"] = layer["words"].pop("w052")
    elif change == "swap":
        ids = list(layer["words"])
        left, right = ids.index("w052"), ids.index("w044")
        ids[left], ids[right] = ids[right], ids[left]
        layer["words"] = {word_id: layer["words"][word_id] for word_id in ids}
    else:
        del layer["words"]["w052"]
    if change != "delete":
        assert layer["words"] == original_entries
    errors = language_packs.check_layer(doc, layer, path)
    assert f"{language}:{TEXT}: word coverage or order differs from the neutral core" in errors
    with pytest.raises(AssertionError):
        assert_target(doc, layer, language)


def test_actual_syntax_consumer_rejects_unsupported_pronoun_head(prayer):
    root, _ = prayer
    doc = read(root / CORE)
    next(word for word in words(doc) if word["id"] == "w052")["head"] = "w044"
    assert (
        f"{TEXT}:w052 (eiúsdem): carries a head but is not a modifier or a preposition"
        in syntax.check(doc)
    )


def test_contract_repair_does_not_promote_pending_analysis_or_working_provenance(prayer):
    root, _ = prayer
    doc = read(root / CORE)
    analysis = doc["editorial"]["words"]["w052"]["analysis"]
    assert analysis == {
        "confidence": "high",
        "sources": ["editorial", "whitakers", "collatinus"],
        "review": "pending",
    }
    for language in ("pl", "en"):
        ledger = read(root / f"languages/{language}/translation-provenance.json")
        assert all(site["review"] == "working" for site in ledger["sites"])
        site = next(site for site in ledger["sites"] if site["segment"] == "s01")
        assert site["origin"] == "working-unsettled" and site["familiar_core"] is False
