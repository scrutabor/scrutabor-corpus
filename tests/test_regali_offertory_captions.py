"""The paired Regali Offertories retain short phrases and declared source slips."""

import json
import shutil
from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from build_reader import bibliography
from build_reader.bibliography_bindings import digest, validate_bindings
from build_reader.layers import enrich_layer, expand_core
from checks import (
    interlinear,
    interlinear_quality,
    interlinear_sequence,
    language_packs,
    prose,
    translation_integrity,
    translation_punctuation,
)
from checks.collate import collate, load_witness
from checks.lint import lint_gloss
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
PASCHAL = "beata-maria-virgo-regina-offertorium"
OUTSIDE = "beata-maria-virgo-regina-extra-tempus-paschale-offertorium"
SLUGS = (PASCHAL, OUTSIDE)
LAYERS = ((PASCHAL, "pl"), (PASCHAL, "en"), (OUTSIDE, "pl"), (OUTSIDE, "en"))
COMMON = (
    "Regáli",
    "ex",
    "progénie",
    "María",
    "exórta",
    "refúlget",
    "cuius",
    "précibus",
    "nos",
    "adiuvári",
    "mente",
    "et",
    "spíritu",
    "devotíssime",
    "póscimus",
)
PROSE = {
    "pl": (
        "Maryja, która wzeszła z królewskiego rodu, jaśnieje; umysłem i duchem "
        "z największą pobożnością prosimy, abyśmy byli wspomagani jej prośbami."
    ),
    "en": (
        "Arisen from a royal lineage, Mary shines forth; with mind and spirit "
        "we most devoutly ask to be helped by her prayers."
    ),
}
NOTES = {
    "pl": (
        "Czasownik póscimus („prosimy”) stoi na końcu zdania. Prośba dotyczy tego, "
        "abyśmy byli wspomagani modlitwami Maryi."
    ),
    "en": (
        "The verb póscimus (“we beg”) comes at the end of the sentence. "
        "The request is that we be helped by Mary’s prayers."
    ),
}
DIRECT = {
    "pl": {
        "w004": "Maryja",
        "w005": "pochodząca",
        "w006": "jaśnieje",
        "w007": "której",
        "w008": "modlitwami",
        "w011": "umysłem",
        "w012": "i",
        "w013": "duchem",
        "w014": "najpobożniej",
        "w015": "prosimy",
        "w016": "Alleluja",
    },
    "en": {
        "w004": "Mary",
        "w005": "sprung",
        "w006": "shines",
        "w011": "in mind",
        "w012": "and",
        "w013": "in spirit",
        "w014": "most devoutly",
        "w015": "we beg",
        "w016": "Alleluia",
    },
}
SEMANTIC = (
    ("pl", "origin"),
    ("pl", "agreement"),
    ("pl", "split"),
    ("pl", "superlative"),
    ("en", "origin"),
    ("en", "possessor"),
    ("en", "passive"),
    ("en", "person"),
    ("en", "split"),
    ("en", "superlative"),
)
STRUCTURAL = (
    ("pl", "residual"),
    ("en", "residual"),
    ("pl", "duplicate"),
    ("en", "duplicate"),
    ("pl", "missing"),
    ("en", "missing"),
    ("pl", "anchor"),
    ("en", "anchor"),
    ("pl", "explanation"),
    ("en", "explanation"),
    ("pl", "semicolon"),
    ("en", "semicolon"),
)


def read(relative):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def load(slug, language):
    core = read(f"texts/proprium/{slug}.json")
    layer = read(f"languages/{language}/texts/proprium/{slug}.json")
    return core, layer


def expected_groups(language):
    groups = [
        {
            "words": ["w001", "w002", "w003"],
            "anchor": "w003",
            "gloss": "Z królewskiego rodu" if language == "pl" else "From a royal line",
        }
    ]
    if language == "en":
        groups.append({"words": ["w007", "w008"], "anchor": "w008", "gloss": "by whose prayers"})
    groups.append(
        {
            "words": ["w009", "w010"],
            "anchor": "w010",
            "gloss": "abyśmy byli wspomagani" if language == "pl" else "that we be helped",
        }
    )
    return groups


def reviewed(core, layer):
    language = layer["language"]
    expected = {
        word["id"]: (
            {"gloss": DIRECT[language][word["id"]]} if word["id"] in DIRECT[language] else {}
        )
        for word in core["segments"][0]["words"]
    }
    expected["w010"]["explanation"] = NOTES[language]
    assert layer["segments"]["s01"]["alignments"] == expected_groups(language), (
        "reviewed short construction"
    )
    assert layer["words"] == expected, "reviewed short construction"
    ending = ""
    if core["id"].endswith(PASCHAL):
        ending = " Alleluja." if language == "pl" else " Alleluia."
    assert layer["segments"]["s01"]["translation"] == PROSE[language] + ending, (
        "retained complete prose"
    )


def healthy(core, layer):
    language = layer["language"]
    path = ROOT / f"languages/{language}/texts/{core['id'].replace('.', '/', 1)}.json"
    doc, enriched = expand_core(core), enrich_layer(core, layer)
    assert language_packs.check_core(core) == []
    assert language_packs.check_layer(core, layer, path) == []
    assert interlinear.check(doc, enriched) == []
    assert interlinear_quality.check(doc, enriched) == []
    assert interlinear_sequence.check(doc, enriched) == []
    assert lint_gloss(enriched, doc) == []
    assert prose.check(layer) == []
    assert translation_punctuation.check(layer) == []
    assert translation_integrity.check(doc, layer) == []
    reviewed(core, layer)


def restore(layer, saved):
    layer.clear()
    layer.update(deepcopy(saved))
    assert layer == saved


@pytest.mark.parametrize(
    "slug,language", LAYERS, ids=("paschal-pl", "paschal-en", "outside-pl", "outside-en")
)
def test_complete_real_layers_keep_prose_topology_and_provenance(slug, language):
    core, layer = load(slug, language)
    healthy(core, layer)
    assert core["localization"]["explanations"] == {"w010": {}}
    sites = read(f"languages/{language}/translation-provenance.json")["sites"]
    (site,) = [row for row in sites if row["site"] == f"{core['id']}.s01.{language}"]
    assert (site["origin"], site["review"], site["familiar_core"]) == (
        "working-unsettled",
        "working",
        False,
    )
    assert site["target_sha256"] == canonical_hash(layer["segments"]["s01"]["translation"])
    assert site["source_sha256"] == canonical_hash(source_payload(expand_core(core)["segments"][0]))


def test_pair_accounts_for_every_latin_and_target_position():
    identities, decisions, groups, members, direct = set(), 0, 0, 0, 0
    for slug in SLUGS:
        core, _ = load(slug, "pl")
        words = core["segments"][0]["words"]
        expected = COMMON + (("Allelúia",) if slug == PASCHAL else ())
        assert tuple(word["form"] for word in words) == expected
        assert [word["id"] for word in words] == [f"w{i:03d}" for i in range(1, len(expected) + 1)]
        posts = {"w006": ";", "w010": ",", "w015": "."}
        if slug == PASCHAL:
            posts["w016"] = "."
        assert {word["id"]: word["post"] for word in words if "post" in word} == posts
        identities.update((core["id"], word["id"]) for word in words)
        by_id = {word["id"]: word for word in words}
        assert by_id["w001"]["head"] == "w003" and by_id["w001"]["morph"]["case"] == "abl"
        assert by_id["w005"]["head"] == "w004" and by_id["w005"]["morph"]["voice"] == "dep"
        assert by_id["w007"]["morph"]["case"] == "gen" and by_id["w008"]["morph"]["number"] == "pl"
        assert by_id["w009"]["morph"] == {"pos": "pron", "case": "acc", "number": "pl"}
        assert {k: by_id["w010"]["morph"][k] for k in ("tense", "voice", "mood")} == {
            "tense": "pres",
            "voice": "pass",
            "mood": "inf",
        }
        assert by_id["w014"]["morph"]["degree"] == "sup"
        assert by_id["w015"]["morph"]["person"] == 1 and by_id["w015"]["morph"]["number"] == "pl"
        for language in ("pl", "en"):
            _, layer = load(slug, language)
            healthy(core, layer)
            counts = {word["id"]: int("gloss" in layer["words"][word["id"]]) for word in words}
            alignments = layer["segments"]["s01"]["alignments"]
            for group in alignments:
                assert 2 <= len(group["words"]) <= 3 and group["anchor"] in group["words"]
                for identifier in group["words"]:
                    counts[identifier] += 1
            assert set(counts.values()) == {1}
            decisions += len(counts)
            groups += len(alignments)
            members += sum(len(group["words"]) for group in alignments)
            direct += sum("gloss" in entry for entry in layer["words"].values())
    assert (len(identities), decisions, groups, members, direct) == (31, 62, 10, 24, 38)


@pytest.mark.parametrize("slug", SLUGS, ids=("paschal", "outside"))
@pytest.mark.parametrize(
    "language,fault",
    SEMANTIC,
    ids=(
        "pl-origin",
        "pl-agreement",
        "pl-split",
        "pl-superlative",
        "en-origin",
        "en-possessor",
        "en-passive",
        "en-person",
        "en-split",
        "en-superlative",
    ),
)
def test_real_caption_damage_is_rejected_and_same_layer_restored(slug, language, fault):
    core, layer = load(slug, language)
    healthy(core, layer)
    saved = deepcopy(layer)
    alignments = layer["segments"]["s01"]["alignments"]
    passive = next(group for group in alignments if group["words"] == ["w009", "w010"])
    try:
        if fault == "origin":
            alignments[0]["gloss"] = (
                "Królewskiego z rodu" if language == "pl" else "Royal from line"
            )
        elif fault == "agreement":
            passive["gloss"] = "nas zostali wsparci"
        elif fault == "possessor":
            alignments[1]["gloss"] = "whose by the prayers"
        elif fault in ("passive", "person"):
            passive["gloss"] = "that we help" if fault == "passive" else "that you be helped"
        elif fault == "superlative":
            layer["words"]["w014"]["gloss"] = "pobożnie" if language == "pl" else "devoutly"
        else:
            assert fault == "split"
            alignments.remove(passive)
            layer["words"]["w009"]["gloss"] = "nas" if language == "pl" else "us"
            layer["words"]["w010"]["gloss"] = (
                "zostali wsparci" if language == "pl" else "to be helped"
            )
        assert layer != saved
        assert interlinear.check(expand_core(core), enrich_layer(core, layer)) == []
        with pytest.raises(AssertionError, match=r"^reviewed short construction(?:\n|$)"):
            reviewed(core, layer)
    finally:
        restore(layer, saved)
        healthy(core, layer)


@pytest.mark.parametrize("slug", SLUGS, ids=("paschal", "outside"))
@pytest.mark.parametrize(
    "language,fault",
    STRUCTURAL,
    ids=(
        "pl-residual",
        "en-residual",
        "pl-duplicate",
        "en-duplicate",
        "pl-missing",
        "en-missing",
        "pl-anchor",
        "en-anchor",
        "pl-explanation",
        "en-explanation",
        "pl-semicolon",
        "en-semicolon",
    ),
)
def test_real_structural_and_prose_guards_reject_damage_and_recover(slug, language, fault):
    core, layer = load(slug, language)
    healthy(core, layer)
    saved = deepcopy(layer)
    groups = layer["segments"]["s01"]["alignments"]
    passive = next(group for group in groups if group["words"] == ["w009", "w010"])
    try:
        if fault == "residual":
            layer["words"]["w009"]["gloss"] = "nas" if language == "pl" else "us"
            needle = "expected exactly one direct gloss or alignment"
        elif fault == "duplicate":
            passive["words"].append("w009")
            needle = "words must be unique"
        elif fault == "missing":
            groups.remove(passive)
            needle = "expected exactly one direct gloss or alignment"
        elif fault == "anchor":
            passive["anchor"] = "w015"
            needle = "anchor must name the source word carrying the gloss"
        elif fault == "explanation":
            del layer["words"]["w010"]["explanation"]
            needle = "explanation topology differs"
        else:
            assert fault == "semicolon"
            layer["words"]["w010"]["explanation"] += ";"
            needle = "uses a semicolon"
        assert layer != saved
        if fault == "explanation":
            path = ROOT / f"languages/{language}/texts/proprium/{slug}.json"
            errors = language_packs.check_layer(core, layer, path)
        elif fault == "semicolon":
            errors = prose.check(layer)
        else:
            errors = interlinear.check(expand_core(core), enrich_layer(core, layer))
        assert any(needle in error for error in errors), errors
    finally:
        restore(layer, saved)
        healthy(core, layer)


@pytest.mark.parametrize(
    "slug,language", LAYERS, ids=("paschal-pl", "paschal-en", "outside-pl", "outside-en")
)
def test_real_seasonal_prose_guard_rejects_acclamation_drift_and_recovers(slug, language):
    core, layer = load(slug, language)
    healthy(core, layer)
    saved = deepcopy(layer)
    acclamation = " Alleluja." if language == "pl" else " Alleluia."
    try:
        layer["segments"]["s01"]["translation"] = PROSE[language] + (
            "" if slug == PASCHAL else acclamation
        )
        assert layer != saved
        errors = translation_integrity.check(expand_core(core), layer)
        assert any("Alleluia(s) in the translation" in error for error in errors), errors
    finally:
        restore(layer, saved)
        healthy(core, layer)


def source_copy(tmp_path, slug):
    directory = tmp_path / slug
    directory.mkdir()
    for name in ("do.txt", "mr.txt", "apparatus.json"):
        shutil.copyfile(ROOT / f"witnesses/proprium.{slug}/{name}", directory / name)
    return directory


def healthy_collation(core, directory):
    errors, warnings, stats = collate(expand_core(core), directory)
    assert errors == warnings == []
    assert stats["witnesses"] == 2 and stats["partial"] == 0
    assert stats["words"] == len(core["segments"][0]["words"])
    assert stats["corrigenda"] == 1 and stats["variants_adjudicated"] == 0
    assert stats["orthographic"] == stats["substantive_variants"] == stats["omissions"] == 0


@pytest.mark.parametrize("slug", SLUGS, ids=("paschal", "outside"))
def test_actual_source_slip_is_a_corrigendum_not_an_apparatus_variant(tmp_path, slug):
    core, _ = load(slug, "pl")
    directory = source_copy(tmp_path, slug)
    healthy_collation(core, directory)
    metadata, digital = load_witness(directory / "do.txt")
    _, printed = load_witness(directory / "mr.txt")
    assert len(metadata["corrigenda"]) == 1
    assert metadata["corrigenda"][0][:2] == ("præscibus", "précibus")
    assert "præscibus" in digital and digital.replace("præscibus", "précibus") == printed
    assert metadata["seasonal-alleluia"] == ("include" if slug == PASCHAL else "omit")
    apparatus = json.loads((directory / "apparatus.json").read_text(encoding="utf-8"))
    assert apparatus["adjudicated"] == [] and apparatus["summary"] == {"entries": 0, "classes": []}
    assert "declared witness-header corrigendum" in apparatus["note"]
    assert "corrigendum header" in core["editorial"]["source"]["method"]
    graph, _ = bibliography.load(ROOT)
    assert validate_bindings(ROOT, graph) == []
    (use,) = [row for row in graph["uses"] if row["id"] == f"use.proprium.{slug}.do44667ff"]
    assert use["evidence_sha256"] == sha256((digital + "\n").encode()).hexdigest()
    assert "præscibus" in use["claim"] and "declared corrigendum to précibus" in use["claim"]
    assert use["verified_on"] == "2026-10-27"
    witnesses = [row for row in graph["witnesses"] if row["text"] == core["id"]]
    assert {row["id"] for row in witnesses} == {
        f"witness.proprium.{slug}.do44667ff",
        f"witness.proprium.{slug}.mr1962",
    }
    for row in witnesses:
        assert row["review"] == {"status": "pending"}
    (row,) = [row for row in graph["collations"] if row["text"] == core["id"]]
    assert row["review"] == {"status": "pending"}
    expected_digest = digest(apparatus)
    assert row["apparatus_sha256"] == expected_digest
    raw_digest = sha256((directory / "apparatus.json").read_bytes()).hexdigest()
    assert raw_digest != expected_digest
    saved = deepcopy(graph)
    try:
        row["apparatus_sha256"] = raw_digest
        assert graph != saved
        errors = validate_bindings(ROOT, graph)
        assert any(
            row["id"] in error and "apparatus_sha256 differs from the complete apparatus" in error
            for error in errors
        ), errors
    finally:
        row["apparatus_sha256"] = expected_digest
        assert graph == saved
        assert validate_bindings(ROOT, graph) == []
    public = bibliography.public_text_evidence(graph)
    (entry,) = [entry for entry in public["texts"] if entry["id"] == core["id"]]
    assert entry["witnesses"] == [] and "collation" not in entry


@pytest.mark.parametrize("slug", SLUGS, ids=("paschal", "outside"))
@pytest.mark.parametrize("fault", ("removed", "stale", "silent", "reason"))
def test_actual_corrigendum_damage_fails_and_restores_same_files(tmp_path, slug, fault):
    core, _ = load(slug, "pl")
    directory = source_copy(tmp_path, slug)
    healthy_collation(core, directory)
    saved = {path.name: path.read_bytes() for path in directory.iterdir()}
    path = directory / "do.txt"
    text = saved["do.txt"].decode()
    (header,) = [line for line in text.splitlines() if line.startswith("# corrigendum:")]
    try:
        if fault == "removed":
            damaged, needle = text.replace(header + "\n", "", 1), "SUBSTANTIVE divergence"
        elif fault == "stale":
            damaged = text.replace(header, header.replace("præscibus ->", "missingtoken ->"), 1)
            needle = "does not print"
        elif fault == "silent":
            lines = text.splitlines(keepends=True)
            damaged = "".join(
                line if line.startswith("#") else line.replace("præscibus", "précibus")
                for line in lines
            )
            needle = "does not print"
        else:
            damaged = text.replace(header, "# corrigendum: præscibus -> précibus", 1)
            needle = "carries no reason"
        assert damaged != text
        path.write_text(damaged, encoding="utf-8")
        assert path.read_bytes() != saved["do.txt"]
        errors, _, _ = collate(expand_core(core), directory)
        assert any(needle in error for error in errors), errors
    finally:
        path.write_bytes(saved["do.txt"])
        assert {path.name: path.read_bytes() for path in directory.iterdir()} == saved
        healthy_collation(core, directory)


@pytest.mark.parametrize("slug", SLUGS, ids=("paschal", "outside"))
@pytest.mark.parametrize("collection", ("witnesses", "collations"))
def test_unreviewed_source_records_cannot_acquire_a_fabricated_seal(slug, collection):
    graph, _ = bibliography.load(ROOT)
    assert validate_bindings(ROOT, graph) == []
    identity = (
        f"witness.proprium.{slug}.do44667ff"
        if collection == "witnesses"
        else f"collation.proprium.{slug}.mr1962-do44667ff"
    )
    (row,) = [row for row in graph[collection] if row["id"] == identity]
    assert row["review"] == {"status": "pending"}
    saved = deepcopy(graph)
    try:
        row["review"] = {"status": "reviewed", "sha256": "0" * 64}
        assert graph != saved
        errors = validate_bindings(ROOT, graph)
        needle = (
            "review requires a complete source inventory"
            if collection == "witnesses"
            else "reviewed collation requires reviewed witness bindings"
        )
        assert any(row["id"] in error and needle in error for error in errors), errors
    finally:
        row["review"] = {"status": "pending"}
        assert graph == saved
        assert validate_bindings(ROOT, graph) == []
