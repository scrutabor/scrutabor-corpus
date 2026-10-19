"""Performer evidence is scoped to an occurrence, not a matching prayer string."""

import copy
import json
import sys
from pathlib import Path

import pytest

from checks import attribute
from checks.raw_binding import resolve_binding

ROOT = Path(__file__).resolve().parent.parent


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    text = (
        json.dumps(value, ensure_ascii=False, indent=2) + "\n" if isinstance(value, dict) else value
    )
    path.write_text(text, encoding="utf-8")
    return path


def document(*verses, text_id="ordinarium.scope-test", category="ordinarium"):
    segments = []
    next_word = 1
    for index, verse in enumerate(verses, 1):
        words = []
        for form in verse.split():
            words.append({"id": f"w{next_word:03d}", "form": form})
            next_word += 1
        segments.append({"id": f"s{index:02d}", "type": "verse", "words": words})
    return {"id": text_id, "category": category, "segments": segments}


def own_source(root, doc, raw, selection=None, name="do"):
    archive = save(root / "witnesses/raw" / f"{name}-scope.txt", raw)
    selection = selection or f"1-{len(raw.splitlines())}"
    save(
        root / "witnesses" / doc["id"] / f"{name}.txt",
        f"# witness: {name}\n# path: {name}-scope.txt (lines {selection})\n"
        + " ".join(
            word["form"]
            for seg in doc["segments"]
            if seg.get("type") == "verse"
            for word in seg["words"]
        )
        + "\n",
    )
    return archive


def marker_source(root, monkeypatch, raw, text_id="ordinarium.test"):
    """A coherent owned header for marker-parser units, not a writer approval."""
    body = raw.read_text(encoding="utf-8")
    archive = save(root / "witnesses/raw/marker-source.txt", body)
    save(
        root / "witnesses" / text_id / "do.txt",
        f"# path: marker-source.txt (lines 1-{len(body.splitlines())})\n" + body,
    )
    monkeypatch.setattr(attribute, "CORPUS", root)
    return archive


def bind_document_source(root, monkeypatch, doc):
    """A controlled complete occurrence for a rule unit, not historical evidence."""
    body = "\n".join(
        " ".join(word["form"] for word in segment["words"])
        for segment in doc["segments"]
        if segment.get("type") == "verse"
    )
    own_source(root, doc, body + "\n")
    monkeypatch.setattr(attribute, "CORPUS", root)


def core_path(root, doc):
    category, slug = doc["id"].split(".", 1)
    return save(root / "texts" / category / f"{slug}.json", doc)


def snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def writer(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["attribute", "--write"])
    return attribute.main()


def test_unscoped_text_cannot_borrow_a_global_response(tmp_path, monkeypatch, capsys):
    doc = document("Amen.")
    path = core_path(tmp_path, doc)
    save(tmp_path / "witnesses/raw/unrelated.txt", "M. Amen.\n")
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    before = snapshot(tmp_path)
    assert not attribute.span_covers(doc)
    assert attribute.marked_lines(doc["id"]) == []
    assert attribute.propose(doc) == {}
    assert writer(monkeypatch) == 1
    assert path.read_bytes() == before[path.relative_to(tmp_path)]
    assert snapshot(tmp_path) == before
    result = attribute.assess(doc)
    assert result.scope == "UNSCOPED" and not result.write_eligible
    assert "UNSCOPED" in capsys.readouterr().out


@pytest.mark.parametrize("selection", ["1,2", "2,1", "1-1, 2-2"])
def test_disjoint_own_text_is_not_performer_authority(tmp_path, monkeypatch, selection):
    doc = document("Lávabo manus meas.", "Sicut erat.")
    for seg in doc["segments"]:
        seg.update(speaker="sacerdos", voice="secreto")
    own_source(tmp_path, doc, "S. Lávabo manus meas.\nM. Sicut erat.\n", selection)
    core_path(tmp_path, doc)
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    before = snapshot(tmp_path)
    assert "speaker" not in attribute.propose(doc).get("s02", {})
    assert attribute.span_covers(doc)  # Textual membership still is not actor evidence.
    assert attribute.assess(doc).scope == "COMPOSITE_TEXT_ONLY"
    assert attribute.marked_lines(doc["id"]) == []
    assert writer(monkeypatch) == 1
    assert snapshot(tmp_path) == before


def test_one_broad_range_cannot_hide_reversed_ritual_occurrences(tmp_path, monkeypatch):
    doc = document("Lávabo manus meas.", "Sicut erat.")
    own_source(tmp_path, doc, "M. Sicut erat.\nS. Lávabo manus meas.\n")
    core_path(tmp_path, doc)
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    before = snapshot(tmp_path)
    assert "speaker" not in attribute.propose(doc).get("s02", {})
    assert attribute.span_covers(doc)
    assert attribute.assess(doc).scope == "STALE_SCOPE"
    assert writer(monkeypatch) == 1
    assert snapshot(tmp_path) == before


def test_actual_lavabo_keeps_the_whole_sicut_priest_and_secret(tmp_path, monkeypatch):
    doc = json.loads((ROOT / "texts/ordinarium/lavabo.json").read_text(encoding="utf-8"))
    path = core_path(tmp_path, doc)
    for source in (ROOT / "witnesses/ordinarium.lavabo").iterdir():
        if source.is_file():
            target = tmp_path / "witnesses/ordinarium.lavabo" / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    raw = ROOT / "witnesses/raw/do-ordo-missae.txt"
    target = tmp_path / "witnesses/raw" / raw.name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(raw.read_bytes())
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    before = snapshot(tmp_path)
    last = next(seg for seg in doc["segments"] if seg["id"] == "s10")
    assert len(last["words"]) == 13
    assert (last["speaker"], last["voice"]) == ("sacerdos", "secreto")
    assert "speaker" not in attribute.propose(doc).get("s10", {})
    assert attribute.assess(doc).scope == "COMPOSITE_TEXT_ONLY"
    assert writer(monkeypatch) == 1
    assert path.read_bytes() == before[path.relative_to(tmp_path)]
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("text_id", ["ordinarium.other-reuse", "proprium.other-secreta"])
def test_reuse_quarantine_is_not_a_lavabo_id_exception(tmp_path, monkeypatch, text_id):
    doc = document("Lávabo.", "Sicut erat.", text_id=text_id)
    own_source(tmp_path, doc, "S. Lávabo.\nM. Sicut erat.\n", "1,2")
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    assert attribute.propose(doc) == {}
    result = attribute.assess(doc)
    assert result.scope == "COMPOSITE_TEXT_ONLY" and not result.write_eligible


def test_absent_voice_preserves_an_existing_fact_while_supported_actor_updates(
    tmp_path, monkeypatch
):
    doc = document("Dóminus.")
    doc["segments"][0].update(speaker="minister", voice="secreto")
    doc["segments"][0]["words"][0]["morph"] = {"voice": "act"}
    doc["segments"][0]["words"] = doc["segments"][0].pop("words")
    path = core_path(tmp_path, doc)
    own_source(tmp_path, doc, "S. Dóminus.\n")
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    protected = {
        p: data for p, data in snapshot(tmp_path).items() if p != path.relative_to(tmp_path)
    }
    status = writer(monkeypatch)
    after = json.loads(path.read_text(encoding="utf-8"))
    assert after["segments"][0].get("voice") == "secreto"
    assert status == 0
    assert after["segments"][0]["speaker"] == "sacerdos"
    expected = copy.deepcopy(doc)
    expected["segments"][0]["speaker"] = "sacerdos"
    assert after == expected
    assert {
        p: data for p, data in snapshot(tmp_path).items() if p != path.relative_to(tmp_path)
    } == protected
    once = path.read_bytes()
    assert writer(monkeypatch) == 0
    assert path.read_bytes() == once


def test_scoped_unknown_actor_preserves_existing_actor_without_promoting_it(tmp_path, monkeypatch):
    doc = document("Dóminus.", text_id="orationes.scope-test", category="orationes")
    doc["segments"][0].update(speaker="omnes", voice="submissa")
    path = core_path(tmp_path, doc)
    own_source(tmp_path, doc, "D. Dóminus.\n")
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    before = path.read_bytes()
    status = writer(monkeypatch)
    assert path.read_bytes() == before
    assert status == 0
    result = attribute.assess(doc)
    assert result.scope == "SCOPED" and result.proposals == {}
    assert attribute.marked_lines(doc["id"], mass=False) == []


@pytest.mark.parametrize("selection", ["0-1", "2-1", "1,1", "1-2,2-3", "1-"])
def test_malformed_scope_is_distinct_from_absent_and_never_falls_back(
    tmp_path, monkeypatch, selection
):
    doc = document("Amen.")
    own_source(tmp_path, doc, "S. Amen.\nM. Other.\nM. Amen.\n", selection)
    core_path(tmp_path, doc)
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    before = snapshot(tmp_path)
    result = attribute.assess(doc)
    assert result.scope == "INVALID_SCOPE" and not result.write_eligible
    assert result.proposals == {} and result.reasons
    assert attribute.marked_lines(doc["id"]) == []
    assert writer(monkeypatch) == 1
    assert snapshot(tmp_path) == before


def test_print_only_is_unknown_not_malformed(tmp_path, monkeypatch):
    doc = document("Amen.")
    save(tmp_path / "witnesses" / doc["id"] / "mr.txt", "# path: printed page 10\nAmen.\n")
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    result = attribute.assess(doc)
    assert result.scope == "UNSCOPED" and result.proposals == {}
    assert not attribute.span_covers(doc)


def test_actual_ordered_kyrie_keeps_all_nine_actors():
    doc = json.loads((ROOT / "texts/ordinarium/kyrie.json").read_text(encoding="utf-8"))
    result = attribute.assess(doc)
    assert result.scope == "SCOPED"
    assert [result.proposals[f"s{index:02d}"]["speaker"] for index in range(2, 11)] == [
        "sacerdos",
        "minister",
        "sacerdos",
        "minister",
        "sacerdos",
        "minister",
        "sacerdos",
        "minister",
        "sacerdos",
    ]


@pytest.mark.parametrize("raw", ["S. Amen. Amen.\n", "S. Testamentum.\n"])
def test_repeated_or_inside_word_hits_do_not_identify_a_unique_occurrence(
    tmp_path, monkeypatch, raw
):
    doc = document("Amen.")
    own_source(tmp_path, doc, raw)
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    assert attribute.assess(doc).scope == "STALE_SCOPE"
    assert attribute.propose(doc) == {}


def test_conflicting_complete_own_witnesses_are_not_a_majority_vote(tmp_path, monkeypatch):
    doc = document("Amen.")
    own_source(tmp_path, doc, "S. Amen.\n", name="priest")
    own_source(tmp_path, doc, "M. Amen.\n", name="server")
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    result = attribute.assess(doc)
    assert result.scope == "COMPOSITE_TEXT_ONLY" and result.proposals == {}


@pytest.mark.parametrize(
    "text_id", ["ordinarium.munda-cor-meum", "ordinarium.iube-domine-benedicere"]
)
def test_actual_hash_heading_readings_stay_textual_only(text_id):
    folder = ROOT / "witnesses" / text_id
    bound = resolve_binding(folder / "do.txt", ROOT)
    assert bound is not None and bound.source["contract"] in {"raw-reading-4", "raw-reading-5"}
    category, slug = text_id.split(".", 1)
    doc = json.loads((ROOT / "texts" / category / f"{slug}.json").read_text(encoding="utf-8"))
    result = attribute.assess(doc)
    assert result.scope == "RAW_TEXT_ONLY" and result.proposals == {}
    assert not result.write_eligible


def test_excluded_office_is_not_an_unresolved_mass_actor():
    doc = document("Amen.", text_id="proprium.vigilia-paschalis-laudes-psalmus")
    result = attribute.assess(doc)
    assert result.scope == "EXCLUDED" and not result.write_eligible
    assert result.proposals == {}


@pytest.mark.parametrize(
    "text_id", ["../outside", "ordinarium../outside", "ordinarium.test/other", None, 0]
)
def test_invalid_text_identity_cannot_open_another_witness_scope(tmp_path, monkeypatch, text_id):
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    doc = document("Amen.", text_id=text_id)
    result = attribute.assess(doc)
    assert result.scope == "INVALID_SCOPE" and result.reasons == ("INVALID_TEXT_ID",)
    assert result.proposals == {} and not result.write_eligible


def test_a_single_verse_crossing_real_actors_is_not_defaulted_to_the_priest(tmp_path, monkeypatch):
    doc = document("Dóminus. Amen.")
    own_source(tmp_path, doc, "S. Dóminus.\nM. Amen.\n")
    core_path(tmp_path, doc)
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    before = snapshot(tmp_path)
    assert attribute.propose(doc) == {}
    assert attribute.span_covers(doc)
    assert attribute.assess(doc).scope == "STALE_SCOPE"
    assert writer(monkeypatch) == 1
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("fault", ["missing-archive", "out-of-bounds"])
def test_claimed_but_unavailable_scope_is_invalid_not_absent(tmp_path, monkeypatch, fault):
    doc = document("Amen.")
    archive = own_source(tmp_path, doc, "S. Amen.\n", "1-2" if fault == "out-of-bounds" else "1")
    if fault == "missing-archive":
        archive.unlink()
    core_path(tmp_path, doc)
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    before = snapshot(tmp_path)
    result = attribute.assess(doc)
    assert result.scope == "INVALID_SCOPE" and result.reasons
    assert result.proposals == {} and attribute.marked_lines(doc["id"]) == []
    assert writer(monkeypatch) == 1
    assert snapshot(tmp_path) == before


def test_a_true_text_boolean_cannot_authorize_an_unscoped_writer(tmp_path, monkeypatch):
    doc = document("Amen.")
    doc["segments"][0].update(speaker="minister", voice="clara")
    core_path(tmp_path, doc)
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    monkeypatch.setattr(attribute, "span_covers", lambda _: True)
    before = snapshot(tmp_path)
    assert attribute.propose(doc) == {}
    assert writer(monkeypatch) == 1
    assert snapshot(tmp_path) == before


def test_a_one_line_short_own_occurrence_cannot_write_the_missing_response(tmp_path, monkeypatch):
    doc = document("Dóminus.", "Amen.")
    for segment in doc["segments"]:
        segment.update(speaker="sacerdos", voice="secreto")
    own_source(tmp_path, doc, "S. Dóminus.\nM. Amen.\n", "1")
    core_path(tmp_path, doc)
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    before = snapshot(tmp_path)
    assert not attribute.span_covers(doc)
    assert attribute.propose(doc) == {}
    assert attribute.assess(doc).scope == "STALE_SCOPE"
    assert writer(monkeypatch) == 1
    assert snapshot(tmp_path) == before


def test_complementary_stale_witnesses_cannot_pool_performer_coverage(tmp_path, monkeypatch):
    doc = document("Dóminus.", "Amen.")
    own_source(tmp_path, doc, "S. Dóminus.\n", name="first")
    own_source(tmp_path, doc, "M. Amen.\n", name="second")
    core_path(tmp_path, doc)
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    before = snapshot(tmp_path)
    assert attribute.span_covers(doc)  # Pooled text remains the legacy comparison only.
    assert attribute.propose(doc) == {}
    assert attribute.assess(doc).scope == "STALE_SCOPE"
    assert writer(monkeypatch) == 1
    assert snapshot(tmp_path) == before


def test_wrapped_two_archive_selection_is_not_one_performer_occurrence(tmp_path, monkeypatch):
    doc = document("Dóminus.", "Amen.")
    save(tmp_path / "witnesses/raw/first.txt", "S. Dóminus.\n")
    save(tmp_path / "witnesses/raw/second.txt", "M. Amen.\n")
    save(
        tmp_path / "witnesses" / doc["id"] / "do.txt",
        "# path: first.txt (line 1), and\n#   second.txt (line 1)\nDóminus. Amen.\n",
    )
    core_path(tmp_path, doc)
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    before = snapshot(tmp_path)
    assert attribute.span_covers(doc)
    assert attribute.assess(doc).scope == "COMPOSITE_TEXT_ONLY"
    assert attribute.propose(doc) == {} and attribute.marked_lines(doc["id"]) == []
    assert writer(monkeypatch) == 1
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("rubric_position", [0, 1, 2])
def test_owned_rule_fixture_ignores_rubric_segments(tmp_path, monkeypatch, rubric_position):
    doc = document("Dóminus.", "Amen.")
    doc["segments"].insert(rubric_position, {"id": "s99", "type": "rubric", "text": "Secreto"})
    bind_document_source(tmp_path, monkeypatch, doc)
    source = tmp_path / "witnesses/raw/do-scope.txt"
    assert source.read_text(encoding="utf-8") == "Dóminus.\nAmen.\n"
    witness = tmp_path / "witnesses" / doc["id"] / "do.txt"
    assert witness.read_text(encoding="utf-8").splitlines()[-1] == "Dóminus. Amen."
    assert attribute.span_covers(doc)
    result = attribute.assess(doc)
    assert result.scope == "SCOPED"
    assert {sid: value["speaker"] for sid, value in result.proposals.items()} == {
        "s01": "sacerdos",
        "s02": "sacerdos",
    }
