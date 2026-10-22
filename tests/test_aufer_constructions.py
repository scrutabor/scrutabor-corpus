"""Finite Aufer constructions and publication boundaries, not general translation rules."""

import json
from collections import Counter
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader import bibliography, store
from build_reader.emit import Table, core_artifact, expand, language_artifact, lexicon_slice
from build_reader.layers import enrich_layer, expand_core
from checks import interlinear, language_packs
from checks.translation_provenance import canonical_hash, check, source_payload, wording_bases

ROOT = Path(__file__).resolve().parents[1]
TEXT = "ordinarium.aufer-a-nobis"
PATH = "texts/ordinarium/aufer-a-nobis.json"
FIXTURE = json.loads((ROOT / "tests/fixtures/aufer-constructions.json").read_text())
MR = "use.ordinarium.aufer-a-nobis.mr1962"
WITHHELD = "use.en.2829f2de97ef8b20d0a3"
BASIS = "use.en.ac9c7a6bd39d21353350"


def load(path, root=ROOT):
    return json.loads((root / path).read_text(encoding="utf-8"))


def write(root, path, value):
    file = root / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")


def require(condition, diagnostic):
    if not condition:
        raise AssertionError(diagnostic)


def word_map(core):
    return {w["id"]: w for s in core["segments"] for w in s.get("words", [])}


def group_for(layer, anchor):
    groups = [
        g
        for s in layer["segments"].values()
        for g in s.get("alignments", [])
        if g.get("anchor") == anchor
    ]
    require(len(groups) == 1, f"group:{anchor}: unique required construction")
    return groups[0]


def assert_core(core):
    words = word_map(core)
    require(words["w032"].get("post") == ",", "latin:selected-relative-comma")
    require(
        [s["id"] for s in core["segments"]] == [f"s{i:02}" for i in range(1, 10)],
        "latin:nine-segment-order",
    )
    require(list(words) == [f"w{i:03}" for i in range(1, 43)], "latin:42-stable-words")
    require(
        canonical_hash(core["segments"]) == FIXTURE["latin_segments_sha256"],
        "latin:complete-source-segments",
    )
    for identifier, case in (("w011", "acc"), ("w012", "gen")):
        require(
            words[identifier]["morph"]["gender"] == "n"
            and words[identifier]["morph"]["case"] == case
            and words[identifier].get("substantive") is True,
            "latin:sanctuary-neuters",
        )
    require(
        words["w013"]["head"] == words["w015"]["id"]
        and words["w013"]["morph"]["case"] == words["w015"]["morph"]["case"] == "abl",
        "latin:interrupted-ablative",
    )
    require(
        words["w014"]["lemma"] == "mereor"
        and words["w014"]["morph"]["mood"] == "subj"
        and words["w016"]["morph"]["mood"] == "inf",
        "latin:worthiness-and-entry",
    )
    require(
        words["w004"]["morph"]["number"] == words["w008"]["morph"]["number"] == "pl"
        and words["w041"]["lemma"] == "meus",
        "latin:first-plural-last-singular",
    )
    require(
        words["w038"]["morph"]["mood"] == "subj"
        and words["w038"]["morph"]["person"] == 2
        and words["w037"]["morph"]["mood"] == "inf",
        "latin:deferential-request",
    )
    require(
        core["editorial"]["notes"] == FIXTURE["editorial_notes"], "editorial:literal-references"
    )
    require(
        canonical_hash({k: v for k, v in core["editorial"].items() if k != "notes"})
        == FIXTURE["editorial_without_notes_sha256"],
        "editorial:no-status-renewal",
    )


def assert_captions(core, layer, language):
    require(interlinear.check(core, layer) == [], f"{language}:complete-once-membership")
    actual = {
        sid: row["alignments"] for sid, row in layer["segments"].items() if row.get("alignments")
    }
    expected = FIXTURE["groups"][language]
    require(list(actual) == list(expected), f"{language}:construction-segments")
    for sid, groups in expected.items():
        require(len(actual[sid]) == len(groups), f"{language}:construction-count:{sid}")
        for got, wanted in zip(actual[sid], groups, strict=True):
            require(got == wanted, f"{language}:construction:{wanted['anchor']}")
            require(
                interlinear.effective_gloss(layer, wanted["anchor"]) == wanted["gloss"],
                f"{language}:effective-anchor:{wanted['anchor']}",
            )
            for wid in wanted["words"]:
                if wid != wanted["anchor"]:
                    require(
                        interlinear.effective_gloss(layer, wid) == "",
                        f"{language}:nonanchor-not-duplicated:{wid}",
                    )
    for wid, gloss in FIXTURE["direct"][language].items():
        require(layer["words"][wid].get("gloss") == gloss, f"{language}:caption:{wid}")
    members = list(FIXTURE["direct"][language]) + [
        wid for groups in actual.values() for group in groups for wid in group["words"]
    ]
    require(Counter(members) == Counter(list(word_map(core))), f"{language}:42-realized-members")


def assert_sources(core, apparatus, graph, english):
    require(word_map(core)["w032"].get("post") == ",", "latin:selected-relative-comma")
    for at in ("w001", "w018", "w032"):
        actual = [r for r in apparatus["adjudicated"] if r["at"] == at]
        expected = [r for r in FIXTURE["apparatus"]["adjudicated"] if r["at"] == at]
        require(actual == expected, f"apparatus:{at}:exact-readings-and-rulings")
    require(apparatus == FIXTURE["apparatus"], "apparatus:complete-four-records")
    uses = {}
    for identifier in (MR, WITHHELD, BASIS):
        matches = [u for u in graph["uses"] + english["uses"] if u["id"] == identifier]
        require(len(matches) == 1, f"source:{identifier}:unique-stable-use")
        uses[identifier] = matches[0]
    require(uses[MR]["role"] == "direct_approved_print", "source:mr:role")
    require(uses[WITHHELD]["decision"] == "REMOVE", "source:1846:withheld")
    for identifier in (MR, WITHHELD, BASIS):
        require(
            uses[identifier] == FIXTURE["source_uses"][identifier],
            f"source:{identifier}:exact-record",
        )
    sites, _texts = wording_bases(english["uses"], "en")
    require(f"{TEXT}.s02.en" in sites, "source:1853:retained-wording-basis")


@pytest.fixture(scope="module")
def baseline():
    core = store.core(ROOT, TEXT)
    graph, languages = bibliography.load(ROOT)
    return {
        "core": core,
        "layers": {lang: store.raw_layer(ROOT, lang, TEXT) for lang in ("pl", "en")},
        "graph": graph,
        "languages": languages,
        "apparatus": load(f"witnesses/{TEXT}/apparatus.json"),
        "dignor_cores": {
            row["text"]: store.core(ROOT, row["text"]) for row in FIXTURE["dignor_contexts"]
        },
    }


@pytest.fixture(scope="module")
def reader(baseline):
    stored = baseline["core"]
    doc = expand_core(stored)
    result = {}
    # Two scoped artifact round trips, once per module; no full reader build.
    for language in ("pl", "en"):
        parses, analyses, shared, local = Table(), Table(), Table(), Table()
        projection = bibliography.ReaderCitationProjection(
            ROOT, baseline["graph"], baseline["languages"]
        )
        core = core_artifact(doc, stored, parses, analyses, shared, projection)
        layer = enrich_layer(stored, baseline["layers"][language])
        artifact = language_artifact(doc, layer, local, projection=projection)
        expanded = expand(core, artifact, parses.order, analyses.order, shared.order, local.order)
        result[language] = {
            "core": core,
            "artifact": artifact,
            "expanded": expanded,
            "parses": parses.order,
            "analyses": analyses.order,
            "shared": shared.order,
            "local": local.order,
            "projection": projection,
            "dignor": lexicon_slice(ROOT, language, {"dignor"})["dignor"],
            "head": lexicon_slice(ROOT, lemmas={"dignor"})["dignor"],
        }
    return result


def test_all_source_words_ritual_boundaries_and_reference_numbers_are_preserved(baseline):
    assert_core(baseline["core"])


@pytest.mark.parametrize("language", ["pl", "en"])
def test_all_realizations_keep_the_eleven_admitted_constructions(baseline, language):
    assert_captions(baseline["core"], baseline["layers"][language], language)


SEMANTIC_CASES = ["sanctuary", "purpose", "worthiness", "first-plural", "last-singular", "saints"]


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("defect", SEMANTIC_CASES)
def test_scoped_semantic_counterexamples_fail_the_owned_assertion(baseline, language, defect):
    layer = deepcopy(baseline["layers"][language])
    frozen = deepcopy((baseline["core"], baseline["layers"], FIXTURE))
    original = deepcopy(layer)
    assert_captions(baseline["core"], layer, language)
    if defect in {"sanctuary", "worthiness"}:
        anchor = "w011" if defect == "sanctuary" else "w014"
        group_for(layer, anchor)["gloss"] = (
            ("świętych ludzi" if language == "pl" else "the holy people")
            if defect == "sanctuary"
            else ("zasłużyliśmy" if language == "pl" else "we earned entry")
        )
        message = f"{language}:construction:{anchor}"
    elif defect in {"purpose", "first-plural"}:
        wid = "w009" if defect == "purpose" else "w004"
        layer["words"][wid]["gloss"] = (
            ("ponieważ" if language == "pl" else "because")
            if defect == "purpose"
            else ("mnie" if language == "pl" else "me")
        )
        message = f"{language}:caption:{wid}"
    elif defect == "last-singular":
        if language == "pl":
            layer["words"]["w041"]["gloss"] = "nasze"
            message = "pl:caption:w041"
        else:
            group_for(layer, "w040")["gloss"] = "our sins"
            message = "en:construction:w040"
    elif language == "pl":
        layer["words"]["w027"]["gloss"] = "Świętych"
        message = "pl:caption:w027"
    else:
        group_for(layer, "w027")["gloss"] = "of Your Saints"
        message = "en:construction:w027"
    require(layer != original, "semantic mutation must change a value")
    with pytest.raises(AssertionError) as error:
        assert_captions(baseline["core"], layer, language)
    assert str(error.value) == message
    layer.clear()
    layer.update(original)
    assert_captions(baseline["core"], layer, language)
    assert (baseline["core"], baseline["layers"], FIXTURE) == frozen


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("defect", ["direct-and-grouped", "noncontiguous", "missing"])
def test_real_interlinear_entrypoint_rejects_membership_damage_and_restores(
    baseline, language, defect
):
    layer = deepcopy(baseline["layers"][language])
    original = deepcopy(layer)
    assert interlinear.check(baseline["core"], layer) == []
    if defect == "direct-and-grouped":
        layer["words"]["w011"]["gloss"] = "duplicated"
        message = f"{TEXT}:w011:{language}: expected exactly one direct gloss or alignment"
    elif defect == "noncontiguous":
        group_for(layer, "w011")["words"] = ["w011", "w013"]
        number = 1 if language == "pl" else 2
        message = (
            f"{TEXT}:s04:alignment-{number}:{language}: "
            "aligned words must be contiguous and in source order"
        )
    else:
        del layer["words"]["w004"]["gloss"]
        message = f"{TEXT}:w004:{language}: expected exactly one direct gloss or alignment"
    assert message in interlinear.check(baseline["core"], layer)
    layer.clear()
    layer.update(original)
    assert interlinear.check(baseline["core"], layer) == []


@pytest.mark.parametrize("language", ["pl", "en"])
def test_effective_explanations_and_shared_card_reach_the_reader(baseline, reader, language):
    expanded = reader[language]["expanded"][1]
    assert baseline["core"]["localization"]["explanations"] == FIXTURE["localization_explanations"]
    for wid, prose in FIXTURE["explanations"][language].items():
        assert expanded["words"][wid]["explanation"] == prose
    card = {**reader[language]["head"], **reader[language]["dignor"]}
    assert reader[language]["head"] == FIXTURE["dignor_head"]
    assert reader[language]["dignor"] == FIXTURE["generic_notes"][language]
    assert card["note"] == FIXTURE["generic_notes"][language]["note"]
    assert word_map(expanded_core := reader[language]["expanded"][0])["w038"]["lemma"] == "dignor"
    assert word_map(expanded_core)["w038"]["morph"]["mood"] == "subj"


@pytest.mark.parametrize("language", ["pl", "en"])
def test_real_language_pack_checker_requires_each_local_explanation(baseline, language):
    core = baseline["core"]
    layer = deepcopy(baseline["layers"][language])
    path = ROOT / f"languages/{language}/{PATH}"
    assert language_packs.check_layer(core, layer, path) == []
    original = deepcopy(layer)
    del layer["words"]["w014"]["explanation"]
    message = f"{language}:{TEXT}: explanation topology differs — missing=['w014'] extra=[]"
    assert message in language_packs.check_layer(core, layer, path)
    layer.clear()
    layer.update(original)
    assert language_packs.check_layer(core, layer, path) == []


@pytest.mark.parametrize("language", ["pl", "en"])
def test_generic_request_note_does_not_reparse_the_eighteen_existing_contexts(
    baseline, reader, language
):
    contexts = FIXTURE["dignor_contexts"]
    assert len({(r["text"], r["word"]) for r in contexts}) == len(contexts) == 18
    cores = baseline["dignor_cores"]
    for row in contexts:
        word = word_map(cores[row["text"]])[row["word"]]
        assert (word["form"], word["lemma"], word["morph"]) == (row["form"], "dignor", row["morph"])
    assert Counter(r["morph"]["mood"] for r in contexts) == {
        "imp": 2,
        "subj": 10,
        "part": 5,
        "ind": 1,
    }
    assert reader[language]["dignor"]["note"] == FIXTURE["generic_notes"][language]["note"]


def test_source_description_distinguishes_selected_comma_and_three_witnesses(baseline):
    assert_sources(
        baseline["core"], baseline["apparatus"], baseline["graph"], baseline["languages"]["en"]
    )


@pytest.mark.parametrize(
    "defect", ["selected-comma", "contradictory-ruling", "mr-role", "1846-revival"]
)
def test_source_controls_reject_independent_corruptions_and_restore(baseline, defect):
    subject = deepcopy(baseline)
    original = deepcopy(subject)
    if defect == "selected-comma":
        word_map(subject["core"])["w032"].pop("post")
        message = "latin:selected-relative-comma"
    elif defect == "contradictory-ruling":
        rows = [r for r in subject["apparatus"]["adjudicated"] if r["at"] == "w032"]
        assert len(rows) == 1
        rows[0]["ruling"] = "No comma before et is selected."
        message = "apparatus:w032:exact-readings-and-rulings"
    else:
        language = subject["graph"] if defect == "mr-role" else subject["languages"]["en"]
        identifier = MR if defect == "mr-role" else WITHHELD
        rows = [r for r in language["uses"] if r["id"] == identifier]
        assert len(rows) == 1
        rows[0]["role" if defect == "mr-role" else "decision"] = (
            "official_text" if defect == "mr-role" else "RETAIN"
        )
        message = "source:mr:role" if defect == "mr-role" else "source:1846:withheld"
    with pytest.raises(AssertionError) as error:
        assert_sources(
            subject["core"], subject["apparatus"], subject["graph"], subject["languages"]["en"]
        )
    assert str(error.value) == message
    subject = deepcopy(original)
    assert_sources(
        subject["core"], subject["apparatus"], subject["graph"], subject["languages"]["en"]
    )
    assert subject == baseline


def test_actual_evidence_projection_withholds_1846_without_losing_1853(baseline, reader):
    package = bibliography.public_text_evidence(baseline["graph"], baseline["languages"]["en"])
    records = [r for r in package["texts"] if r["id"] == TEXT]
    assert len(records) == 1
    entries = {e["id"]: e for g in records[0]["source_groups"] for e in g["entries"]}
    assert WITHHELD not in entries and BASIS in entries
    row = next(r for r in reader["en"]["artifact"]["seg"] if r["id"] == "s02")
    citations = [reader["en"]["local"][i] for i in row["tc"]]
    assert citations == [baseline["layers"]["en"]["segments"]["s02"]["translation_citations"][0]]
    assert records[0]["witnesses"] == [] and "collation" not in records[0]
    neutral = bibliography.public_text_evidence(baseline["graph"])
    neutral_rows = [r for r in neutral["texts"] if r["id"] == TEXT]
    assert len(neutral_rows) == 1
    mr_groups = [
        g for g in neutral_rows[0]["source_groups"] if any(e["id"] == MR for e in g["entries"])
    ]
    assert len(mr_groups) == 1 and mr_groups[0]["role"] == "direct_approved_print"
    assert neutral_rows[0]["witnesses"] == [] and "collation" not in neutral_rows[0]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_all_prose_rubrics_and_provenance_remain_exact_without_status_renewal(baseline, language):
    layer = baseline["layers"][language]
    actual = {
        sid: {k: v for k, v in row.items() if k != "alignments"}
        for sid, row in layer["segments"].items()
    }
    assert actual == FIXTURE["preserved_layers"][language]
    rows = [
        r
        for r in load(f"languages/{language}/translation-provenance.json")["sites"]
        if r["text"] == TEXT
    ]
    assert rows == FIXTURE["preserved_provenance"][language]
    for row in rows:
        segment = next(s for s in baseline["core"]["segments"] if s["id"] == row["segment"])
        assert row["source_sha256"] == canonical_hash(source_payload(segment))
        assert row["target_sha256"] == canonical_hash(
            layer["segments"][row["segment"]]["translation"]
        )


@pytest.fixture(scope="module")
def provenance_root(tmp_path_factory, baseline):
    root = tmp_path_factory.mktemp("aufer-provenance")
    write(root, PATH, baseline["core"])
    write(root, "bibliography/graph.json", baseline["graph"])
    for language in ("pl", "en"):
        prefix = f"languages/{language}/"
        write(root, prefix + PATH, baseline["layers"][language])
        manifest = load(prefix + "manifest.json")
        manifest["texts"] = [TEXT]
        write(root, prefix + "manifest.json", manifest)
        ledger = load(prefix + "translation-provenance.json")
        ledger["sites"] = [r for r in ledger["sites"] if r["text"] == TEXT]
        write(root, prefix + "translation-provenance.json", ledger)
        write(root, prefix + "bibliography.json", baseline["languages"][language])
    return root


@pytest.mark.parametrize("language", ["pl", "en"])
@pytest.mark.parametrize("defect", ["source", "target", "wording-basis"])
def test_real_provenance_entrypoint_rejects_staleness_or_lost_basis(
    provenance_root, language, defect
):
    root = provenance_root
    assert check(root) == ([], {"public-domain": 9, "working-unsettled": 1})
    path = PATH if defect == "source" else f"languages/{language}/{PATH}"
    if defect == "wording-basis":
        path = f"languages/{language}/bibliography.json"
    file = root / path
    original = file.read_bytes()
    changed = load(path, root)
    if defect == "source":
        word_map(changed)["w001"]["form"] = "Orátis"
        message = f"{TEXT}.s02.{language}: stale source_sha256"
    elif defect == "target":
        changed["segments"]["s02"]["translation"] += " Added claim."
        message = f"{TEXT}.s02.{language}: stale target_sha256"
    else:
        matches = [
            u
            for u in changed["uses"]
            if u["role"] == "historical_wording_basis"
            and u.get("address", {}).get("text") == TEXT
            and u["address"].get("segment") in {None, "s02"}
        ]
        assert matches
        for use in matches:
            use["decision"] = "REMOVE"
        message = f"{TEXT}.s02.{language}: origin=public-domain requires a wording citation"
    try:
        write(root, path, changed)
        errors, tally = check(root)
        assert tally == {"public-domain": 9, "working-unsettled": 1}
        assert message in errors
    finally:
        file.write_bytes(original)
    assert file.read_bytes() == original
    assert check(root) == ([], {"public-domain": 9, "working-unsettled": 1})


@pytest.mark.parametrize("language", ["pl", "en"])
def test_scoped_reader_roundtrip_preserves_caps_groups_and_all_help(baseline, reader, language):
    doc, layer = reader[language]["expanded"]
    assert_captions(doc, layer, language)
    for wid, explanation in FIXTURE["explanations"][language].items():
        assert layer["words"][wid]["explanation"] == explanation
    assert doc["segments"] == expand_core(baseline["core"])["segments"]


@pytest.mark.parametrize("language", ["pl", "en"])
def test_dropped_emitted_help_is_detected_and_immutable_baseline_restored(reader, language):
    view = reader[language]
    original = deepcopy(view["artifact"])
    mutant = deepcopy(original)
    rows = [r for r in mutant["seg"] if r["id"] == "s04"]
    require(len(rows) == 1, f"{language}:reader:s04:unique-stable-segment")
    row = rows[0]
    require(
        row.get("ex", {}).get("w014") == FIXTURE["explanations"][language]["w014"],
        f"{language}:reader:w014:healthy-admitted-help",
    )
    del row["ex"]["w014"]
    _doc, layer = expand(
        view["core"], mutant, view["parses"], view["analyses"], view["shared"], view["local"]
    )
    require("explanation" not in layer["words"]["w014"], "help mutation must reach real decoder")
    with pytest.raises(AssertionError) as error:
        require(
            layer["words"]["w014"].get("explanation") == FIXTURE["explanations"][language]["w014"],
            f"{language}:reader:w014:missing-admitted-help",
        )
    assert str(error.value) == f"{language}:reader:w014:missing-admitted-help"
    assert view["artifact"] == original
