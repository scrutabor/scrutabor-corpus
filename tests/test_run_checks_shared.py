"""Global prerequisites stay fresh through the real single-text entry point."""

import json
import shutil
from pathlib import Path

import pytest

import checks.attribute
import run_checks as runner
from build_reader import store

CORPUS = Path(__file__).resolve().parent.parent
TEXT = "ordinarium.confiteor"


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False) + "\n", encoding="utf-8")


@pytest.fixture
def single_text_corpus(tmp_path, monkeypatch):
    """Real text, layers, lexica and witnesses, with only its package coverage.

    No validator result is replaced. The legacy raw-source resolver has its
    own corpus setting, which must name the same isolated source root.
    """
    relative = "texts/ordinarium/confiteor.json"
    (tmp_path / relative).parent.mkdir(parents=True)
    shutil.copyfile(CORPUS / relative, tmp_path / relative)
    shutil.copytree(CORPUS / "lexicon", tmp_path / "lexicon")
    for language in ("pl", "en"):
        package = tmp_path / "languages" / language
        (package / relative).parent.mkdir(parents=True)
        shutil.copyfile(CORPUS / "languages" / language / relative, package / relative)
        for filename in ("lexicon.json", "translation-basis.json", "translation-provenance.json"):
            shutil.copyfile(CORPUS / "languages" / language / filename, package / filename)
        manifest = json.loads(
            (CORPUS / "languages" / language / "manifest.json").read_text(encoding="utf-8")
        )
        assert TEXT in manifest["texts"]
        manifest["texts"] = [TEXT]
        manifest["titles"] = {
            text: metadata for text, metadata in manifest.get("titles", {}).items() if text == TEXT
        }
        write_json(package / "manifest.json", manifest)
    shutil.copytree(CORPUS / "witnesses" / TEXT, tmp_path / "witnesses" / TEXT)
    raw = tmp_path / "witnesses/raw"
    raw.mkdir()
    shutil.copyfile(CORPUS / "witnesses/raw/do-ordo-missae.txt", raw / "do-ordo-missae.txt")
    monkeypatch.setattr(runner, "CORPUS", tmp_path)
    monkeypatch.setattr(checks.attribute, "CORPUS", tmp_path)
    yield tmp_path
    # Never clear between successive calls: the public entry owns freshness.
    store._manifest.cache_clear()
    store._translation_relationships.cache_clear()


def check_text(capsys, expected):
    result = runner.main(TEXT)
    output = capsys.readouterr().out
    assert result == expected, output
    verdict = "OK" if expected == 0 else "FAIL"
    words = sum(
        len(segment.get("words") or []) for segment in store.core(runner.CORPUS, TEXT)["segments"]
    )
    assert words > 0
    assert f"VERDICT {verdict} text={TEXT} words={words} " in output
    assert "langs=en,pl witnesses=3" in output
    return output


def test_single_text_uses_actual_global_inputs_once(single_text_corpus, monkeypatch, capsys):
    calls = []
    loaded = []
    for name in ("check_language_manifests", "check_schema_versions", "load_lexicon"):
        actual = getattr(runner, name)

        def measured(*args, _name=name, _actual=actual, **kwargs):
            calls.append(_name)
            result = _actual(*args, **kwargs)
            if _name == "load_lexicon":
                loaded.append(result)
            return result

        monkeypatch.setattr(runner, name, measured)
    actual_text = runner._check_text
    dispatched = []

    def measured_text(text_id, lemmata, global_errors=()):
        assert text_id == TEXT
        assert len(loaded) == 1 and lemmata is loaded[0][0]
        assert not global_errors
        dispatched.append(text_id)
        return actual_text(text_id, lemmata, global_errors)

    monkeypatch.setattr(runner, "_check_text", measured_text)
    check_text(capsys, 0)
    assert dispatched == [TEXT]
    assert sorted(calls) == [
        "check_language_manifests",
        "check_schema_versions",
        "load_lexicon",
    ]


@pytest.mark.parametrize("fault", ["schema", "manifest", "lexicon-language", "missing-lemma"])
def test_single_text_rejects_current_disk_fault_and_accepts_exact_restoration(
    single_text_corpus, capsys, fault
):
    root = single_text_corpus
    check_text(capsys, 0)
    if fault == "schema":
        path = root / "languages/pl/lexicon.json"
        diagnostic = "schema_version differs across the corpus"
    elif fault == "manifest":
        path = root / "languages/pl/manifest.json"
        diagnostic = "languages/pl/manifest.json: direction must be ltr or rtl"
    elif fault == "lexicon-language":
        path = root / "languages/pl/lexicon.json"
        diagnostic = "languages/pl/lexicon.json: language does not match its directory"
    else:
        path = root / "lexicon/lemmata.json"
        diagnostic = "lemma 'confiteor' has no lexicon entry"
    before = path.read_bytes()
    document = json.loads(before)
    if fault == "schema":
        document["schema_version"] = "0.0.0"
    elif fault == "manifest":
        # The initial call already populated store's manifest cache. This
        # mutation must be discovered by another public invocation anyway.
        assert store.language_manifest(root, "pl")["direction"] == "ltr"
        document["direction"] = "invalid"
    elif fault == "lexicon-language":
        document["language"] = "en"
    else:
        assert any(
            word["lemma"] == "confiteor"
            for segment in store.core(root, TEXT)["segments"]
            for word in segment.get("words") or []
        )
        del document["entries"]["confiteor"]
    try:
        write_json(path, document)
        assert path.read_bytes() != before
        output = check_text(capsys, 1)
        assert diagnostic in output
    finally:
        path.write_bytes(before)
    assert path.read_bytes() == before
    output = check_text(capsys, 0)
    assert diagnostic not in output


@pytest.mark.parametrize("entry_point", ["single", "all"])
def test_lexicon_hole_is_diagnosed_before_loading(single_text_corpus, capsys, entry_point):
    root = single_text_corpus
    check_text(capsys, 0)
    path = root / "languages/pl/lexicon.json"
    before = path.read_bytes()
    data = json.loads(before)
    data["entries"]["confiteor"] = None
    try:
        write_json(path, data)
        assert (runner.main(TEXT) if entry_point == "single" else runner.run_all()) == 1
        output = capsys.readouterr().out
        assert "VERDICT FAIL lexicon" in output
        assert "confiteor" in output and "ERROR:" in output
        assert "Traceback" not in output
    finally:
        path.write_bytes(before)
    assert path.read_bytes() == before
    check_text(capsys, 0)
