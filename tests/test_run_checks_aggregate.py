"""Production aggregate orchestration: keep all neutral documents and failures."""

from types import SimpleNamespace

import pytest

import checks.disputed
import run_checks as runner

LATE = (
    "uncertainty",
    "history",
    "registry",
    "addresses",
    "witness",
    "bibliography",
    "rights_load",
    "rights",
    "titles",
    "floor",
    "provenance",
    "basis",
    "kalendarium",
    "formularies",
)


@pytest.fixture
def configured(monkeypatch, tmp_path):
    def configure(missing=None, failure=None):
        ids = ["fixture.complete", "fixture.incomplete"]
        docs = [{"id": tid, "segments": [{"words": [{"lemma": tid}]}]} for tid in ids]
        layers = [
            {"en": {"language": "en"}, "pl": {"language": "pl"}},
            {"en": {"language": "en"}, "pl": {"language": "pl"}},
        ]
        if missing == "en":
            del layers[1]["en"]
        elif missing == "all":
            layers[1] = {}
        events = []
        monkeypatch.setenv("SCRUTABOR_BASE", "fixture-reference")
        monkeypatch.setattr(runner, "CORPUS", tmp_path)
        monkeypatch.setattr(runner, "discover", lambda: list(ids))
        monkeypatch.setattr(
            runner.store, "load", lambda root, tid: (docs[ids.index(tid)], layers[ids.index(tid)])
        )
        monkeypatch.setattr(
            runner.store, "all_texts", lambda root: list(zip(docs, layers, strict=True))
        )
        monkeypatch.setattr(runner, "load_lexicon", lambda root: ({}, {}))

        def event(name, value=None):
            events.append(name)
            return ["injected " + name] if failure == name else []

        def lexical(used):
            assert used == set(ids)
            event("lexicon")
            return int(failure == "lexicon")

        def per_text(tid):
            event("text:" + tid)
            return int((missing is not None and tid == ids[1]) or failure == "per_text")

        def uncertainty(corpus_docs):
            assert corpus_docs == docs
            return event("uncertainty")

        def path_check(name):
            def check(root, *args):
                assert root == tmp_path
                if name in ("history", "registry"):
                    assert args == ("fixture-reference",)
                if name == "addresses":
                    assert args == ({*ids},)
                return event(name)

            return check

        def cited_check(name):
            def check(cited, *args):
                assert cited[:2] == docs
                assert cited[2:] == [g for layer in layers for g in layer.values()]
                return event(name)

            return check

        monkeypatch.setattr(runner, "lexicon_suite", lexical)
        monkeypatch.setattr(runner, "main", per_text)
        monkeypatch.setattr(runner, "check_uncertainty", uncertainty)
        monkeypatch.setattr(runner, "resolve_ref", lambda root, base: "fixture-sha")
        for attr, name in [
            ("check_against_history", "history"),
            ("check_registry_history", "registry"),
            ("check_addresses", "addresses"),
            ("check_witness_archive", "witness"),
            ("check_bibliography", "bibliography"),
            ("check_explanation_floor", "floor"),
        ]:
            monkeypatch.setattr(runner, attr, path_check(name))
        monkeypatch.setattr(runner, "load_rights", lambda root: ({}, event("rights_load")))
        monkeypatch.setattr(runner, "check_rights", cited_check("rights"))
        monkeypatch.setattr(runner, "check_citation_titles", cited_check("titles"))

        def rights_exposure(cited, works):
            assert cited[:2] == docs
            event("rights_exposure")
            return {}

        monkeypatch.setattr(runner, "rights_exposure", rights_exposure)
        monkeypatch.setattr(
            runner, "check_translation_provenance", lambda root: (event("provenance"), {})
        )
        monkeypatch.setattr(runner, "check_translation_basis", lambda root: (event("basis"), {}))
        monkeypatch.setattr(runner, "check_kalendarium", lambda root: (event("kalendarium"), 0, 0))
        monkeypatch.setattr(runner, "check_formularies", lambda root: (event("formularies"), {}))

        def readings(corpus_docs):
            assert corpus_docs == docs
            event("readings")
            return {}

        monkeypatch.setattr(runner, "readings", readings)
        monkeypatch.setattr(runner, "exposure", lambda doc, attested: int(doc in docs))
        monkeypatch.setattr(runner, "stored", lambda doc: int(doc in docs))
        monkeypatch.setattr(checks.disputed, "collect", lambda: (event("disputed") and {}) or {})
        return SimpleNamespace(ids=ids, docs=docs, layers=layers, events=events)

    return configure


def assert_all_checks(fixture):
    assert fixture.events == [
        "lexicon",
        "text:fixture.complete",
        "text:fixture.incomplete",
        "uncertainty",
        "history",
        "registry",
        "addresses",
        "witness",
        "bibliography",
        "rights_load",
        "rights",
        "titles",
        "rights_exposure",
        "floor",
        "provenance",
        "basis",
        "kalendarium",
        "formularies",
        "readings",
        "disputed",
    ]


def test_complete_aggregate_can_pass(configured):
    fixture = configured()
    assert runner.run_all() == 0
    assert_all_checks(fixture)


@pytest.mark.parametrize("missing", ["en", "all"])
def test_missing_layer_upstream_failure_keeps_every_core_and_later_checks(configured, missing):
    # rc=1 models the per-text error; English is not universally mandatory
    # for an otherwise valid independently published PL-only edition.
    fixture = configured(missing=missing)
    assert runner.run_all() == 1
    assert_all_checks(fixture)


@pytest.mark.parametrize("failure", ["lexicon", "per_text", *LATE])
def test_any_earlier_or_later_failure_is_retained(configured, failure):
    fixture = configured(failure=failure)
    assert runner.run_all() == 1
    assert_all_checks(fixture)


def test_zero_documents_cannot_pass(monkeypatch):
    monkeypatch.setattr(runner, "discover", lambda: [])
    assert runner.run_all() == 1
