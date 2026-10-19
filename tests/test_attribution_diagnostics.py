"""Rubric/law findings are not performer authority or permission to write."""

import json
from pathlib import Path

import pytest
import test_attribution_alignment as alignment_tests
from test_attribution_scope import core_path, document, own_source, snapshot, writer

from checks import attribute, office, ritual

ROOT = Path(__file__).resolve().parent.parent
reading = alignment_tests.reading
PANEM_WARNINGS = [
    "ordinarium.panem-caelestem.s07: the text's rubric reads secreto, "
    "RG 511 i — the second time rules clara",
    "ordinarium.panem-caelestem.s10: the text's rubric reads secreto, "
    "RG 511 i — the third time rules clara",
]


def forbidden(*args, **kwargs):
    pytest.fail("diagnostics must not discover or rescue performer evidence")


def ruled_document(monkeypatch, rubric="Secreto"):
    doc = document("Amen.")
    doc["segments"].insert(0, {"id": "s00", "type": "rubric", "text": rubric})
    monkeypatch.setitem(attribute.VOICE_RULINGS, doc["id"], ("clara", "fixture law"))
    return doc


def test_actual_panem_reports_both_disagreements_without_authority():
    doc = json.loads((ROOT / "texts/ordinarium/panem-caelestem.json").read_text())
    baseline = attribute.assess(doc)
    assert baseline.scope == "COMPOSITE_TEXT_ONLY"
    assert baseline.reasons == ("COMPOSITE_LEGACY_READING:do.txt: 328, 330-332, 335",)
    assert baseline.proposals == {} and not baseline.write_eligible
    messages = ["existing finding"]
    measured = attribute.assess(doc, messages)
    assert measured == baseline
    assert messages == ["existing finding", *PANEM_WARNINGS]
    wrapped = []
    assert attribute.propose(doc, wrapped) == {}
    assert wrapped == PANEM_WARNINGS


def test_actual_panem_writer_reports_but_preserves_all_fixture_bytes(tmp_path, monkeypatch, capsys):
    path = ROOT / "texts/ordinarium/panem-caelestem.json"
    target = tmp_path / path.relative_to(ROOT)
    target.parent.mkdir(parents=True)
    target.write_bytes(path.read_bytes())
    for source in (ROOT / "witnesses/ordinarium.panem-caelestem").iterdir():
        dest = tmp_path / source.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(source.read_bytes())
    source = ROOT / "witnesses/raw/do-ordo-missae.txt"
    dest = tmp_path / source.relative_to(ROOT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(source.read_bytes())
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    before = snapshot(tmp_path)
    assert writer(monkeypatch) == 1
    assert snapshot(tmp_path) == before
    printed = capsys.readouterr().out.splitlines()
    assert [line for line in printed if line.startswith("DISAGREES  ")] == [
        "DISAGREES  " + warning for warning in PANEM_WARNINGS
    ]
    assert "changed 0 fields; preserved 1 unresolved texts" in printed


@pytest.mark.parametrize(
    "scope",
    ["UNSCOPED", "INVALID_SCOPE", "STALE_SCOPE", "COMPOSITE_TEXT_ONLY", "RAW_TEXT_ONLY"],
)
def test_quarantined_rule_findings_never_become_proposals_or_writes(
    tmp_path, monkeypatch, capsys, scope
):
    # Inject each assessment boundary, not a fabricated raw contract.
    doc = ruled_document(monkeypatch)
    doc["segments"][1].update(speaker="omnes", voice="submissa")
    core_path(tmp_path, doc)
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    monkeypatch.setattr(
        attribute, "_actor_sources", lambda _: attribute._ActorSources(scope, (), ("fixture",))
    )
    for name in ("_owned_speakers", "span_covers", "align_unmarked_reading", "marked_lines"):
        monkeypatch.setattr(attribute, name, forbidden)
    before = snapshot(tmp_path)
    messages = []
    result = attribute.assess(doc, messages)
    assert (result.scope, result.reasons, result.proposals, result.write_eligible) == (
        scope,
        ("fixture",),
        {},
        False,
    )
    assert messages == [
        "ordinarium.scope-test.s01: the text's rubric reads secreto, fixture law rules clara"
    ]
    assert writer(monkeypatch) == 1
    assert snapshot(tmp_path) == before
    assert capsys.readouterr().out.count("DISAGREES  ") == 1


@pytest.mark.parametrize("selection", [None, "1-"], ids=["unscoped", "invalid-selection"])
def test_real_source_refusal_does_not_use_diagnostic_rules_as_fallback(
    tmp_path, monkeypatch, selection
):
    doc = ruled_document(monkeypatch)
    if selection is not None:
        own_source(tmp_path, doc, "S. Amen.\n", selection)
    else:
        unrelated = tmp_path / "witnesses/raw/unrelated.txt"
        unrelated.parent.mkdir(parents=True)
        unrelated.write_text("M. Amen.\n")
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    monkeypatch.setattr(attribute, "marked_lines", forbidden)
    monkeypatch.setattr(attribute, "align_unmarked_reading", forbidden)
    messages = []
    result = attribute.assess(doc, messages)
    assert result.scope == ("UNSCOPED" if selection is None else "INVALID_SCOPE")
    assert result.proposals == {} and not result.write_eligible
    assert messages == [
        "ordinarium.scope-test.s01: the text's rubric reads secreto, fixture law rules clara"
    ]


@pytest.mark.parametrize(
    "kind,expected_voice,expected_messages",
    [
        ("segment", "submissa", ["fixture segment rules submissa"]),
        ("general", "clara", ["fixture law rules clara"]),
        ("rubric", "secreto", []),
        ("unsettled", None, []),
        ("agreement", "clara", []),
    ],
    ids=["segment", "general", "rubric", "unsettled", "agreement"],
)
def test_scoped_precedence_and_once_only_reporting(
    tmp_path, monkeypatch, kind, expected_voice, expected_messages
):
    doc = ruled_document(monkeypatch, "Clara voce" if kind == "agreement" else "Secreto")
    own_source(tmp_path, doc, "S. Amen.\n")
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    ref = doc["id"] + ".s01"
    if kind == "segment":
        monkeypatch.setitem(attribute.VOICE_SEGMENT_RULINGS, ref, ("submissa", "fixture segment"))
    elif kind == "rubric":
        monkeypatch.delitem(attribute.VOICE_RULINGS, doc["id"])
    elif kind == "unsettled":
        monkeypatch.setitem(attribute.VOICE_UNSETTLED, ref, "fixture unsettled")
    messages = []
    result = attribute.assess(doc, messages)
    assert result.scope == "SCOPED" and result.write_eligible
    expected = {"speaker": "sacerdos"}
    if expected_voice is not None:
        expected["voice"] = expected_voice
    assert result.proposals == {"s01": expected}
    prefix = doc["id"] + ".s01: the text's rubric reads secreto, "
    assert messages == [prefix + tail for tail in expected_messages]


@pytest.mark.parametrize("scoped", [False, True], ids=["quarantined", "scoped"])
def test_modeled_oration_diagnostics_do_not_depend_on_performer_eligibility(
    tmp_path, monkeypatch, scoped
):
    doc = document(
        "Praesta nobis quaesumus Deus.",
        "Per omnia saecula saeculorum.",
        "Amen.",
        text_id="proprium.fixture-secreta",
        category="proprium",
    )
    doc["segments"].insert(0, {"id": "s00", "type": "rubric", "text": "Secreto"})
    if scoped:
        own_source(
            tmp_path,
            doc,
            "S. Praesta nobis quaesumus Deus.\nS. Per omnia saecula saeculorum.\nM. Amen.\n",
        )
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    messages = []
    result = attribute.assess(doc, messages)
    assert result.scope == ("SCOPED" if scoped else "UNSCOPED")
    assert result.write_eligible is scoped
    assert messages == [
        f"proprium.fixture-secreta.{sid}: the text's rubric reads secreto, "
        "RG 480–481, 511 d/i; Ordo Missae conclusion rules clara"
        for sid in ("s02", "s03")
    ]
    if scoped:
        assert result.proposals == {
            "s01": {"speaker": "sacerdos", "voice": "secreto"},
            "s02": {"speaker": "sacerdos", "voice": "clara"},
            "s03": {"speaker": "minister", "voice": "clara"},
        }
    else:
        assert result.proposals == {}


def test_malformed_oration_has_no_invented_boundary_warning(tmp_path, monkeypatch):
    doc = document("Amen.", text_id="proprium.fixture-secreta", category="proprium")
    doc["segments"].insert(0, {"id": "s00", "type": "rubric", "text": "Clara voce"})
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    messages = []
    result = attribute.assess(doc, messages)
    assert result.scope == "UNSCOPED" and result.proposals == {}
    assert messages == [
        "proprium.fixture-secreta.s01: the text's rubric reads clara, RG 511 — cetera rules secreto"
    ]


def test_actual_aligned_source_keeps_unsourced_oration_precedence(reading, monkeypatch):
    root, folder, data = reading
    doc = data["document"]
    alignment_tests.source_checks(root, folder, doc)
    baseline = attribute.assess(doc)
    assert baseline.scope == "ALIGNED" and baseline.alignment is not None
    assert len(baseline.alignment.words) == 219
    # Alignment requires exactly one complete verse. Do not add a rubric
    # segment that would invalidate its real source contract. This injected
    # rubric observation tests diagnostic precedence, not historical wording.
    sid = doc["segments"][0]["id"]
    monkeypatch.setattr(attribute, "voice_of", lambda _doc, _index: "secreto")
    monkeypatch.setattr(
        attribute,
        "oration_attributes",
        lambda _: {sid: {"speaker": "minister", "voice": "secreto"}},
    )
    messages = []
    result = attribute.assess(doc, messages)
    assert result == baseline
    assert messages == [f"{doc['id']}.{sid}: the text's rubric reads secreto, RG 511 e rules clara"]


@pytest.mark.parametrize("kind", ["office", "ritual", "no-verses"])
def test_exclusions_stay_outside_ordinary_diagnostics(monkeypatch, kind):
    doc = ruled_document(monkeypatch)
    if kind == "office":
        monkeypatch.setattr(office, "TEXTS", frozenset({doc["id"]}))
    elif kind == "ritual":
        monkeypatch.setattr(ritual, "TEXTS", frozenset({doc["id"]}))
        monkeypatch.setattr(ritual, "base_errors", lambda _: [])
    else:
        doc["segments"] = doc["segments"][:1]
    monkeypatch.setattr(attribute, "_actor_sources", forbidden)
    monkeypatch.setattr(attribute, "_voice_rules", forbidden, raising=False)
    messages = ["existing finding"]
    result = attribute.assess(doc, messages)
    assert result.scope == "EXCLUDED" and result.proposals == {}
    assert not result.write_eligible
    assert messages == ["existing finding"]


def test_invalid_ritual_still_raises_before_ordinary_diagnostics(monkeypatch):
    doc = ruled_document(monkeypatch)
    monkeypatch.setattr(ritual, "TEXTS", frozenset({doc["id"]}))
    monkeypatch.setattr(ritual, "base_errors", lambda _: ["fixture ritual refusal"])
    monkeypatch.setattr(attribute, "_voice_rules", forbidden, raising=False)
    messages = []
    with pytest.raises(ValueError, match=r"^fixture ritual refusal$"):
        attribute.assess(doc, messages)
    assert messages == []


@pytest.mark.parametrize("text_id", [None, 0, "../outside"], ids=["null", "number", "path"])
def test_invalid_identity_stays_refused_without_rule_lookup(monkeypatch, text_id):
    doc = document("Amen.", text_id=text_id)
    monkeypatch.setattr(attribute, "_voice_rules", forbidden, raising=False)
    monkeypatch.setattr(attribute, "oration_attributes", forbidden)
    messages = ["existing finding"]
    result = attribute.assess(doc, messages)
    assert result.scope == "INVALID_SCOPE" and result.reasons == ("INVALID_TEXT_ID",)
    assert result.proposals == {} and not result.write_eligible
    assert messages == ["existing finding"]
