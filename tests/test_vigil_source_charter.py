"""Selected source rules and the unchanged fail-closed article requirement."""

import re
import shutil
from pathlib import Path

import pytest

from checks import kalendarium as checker

ROOT = Path(checker.__file__).resolve().parent.parent


CRITICAL_CLAUSES = {
    33: (
        "33. Vigilia II aut III classis penitus omittitur, si occurrat in dominica "
        "quavis, aut in festo I classis, vel si festum cui praemittitur in alium diem "
        "transferri aut ad commemorationem reduci contingat."
    ),
    93: (
        "93. Effectus occurrentiae est, ut Officium diei liturgici gradus inferioris "
        "Officio gradus superioris cedat: quod fieri potest per minus nobilis omissionem, "
        "aut commemorationem, aut translationem, aut repositionem, prout numeris "
        "sequentibus indicatur."
    ),
    95: (
        "Si vero duo festa eiusdem Divinae Personae aut duo festa eiusdem Sancti vel Beati "
        "simul occurrunt, fit de festo, quod in tabella praecedentiae superiorem obtinet "
        "locum, et aliud omittitur."
    ),
}
MESSAGES = {
    33: "Benziger33 omission clause differs from the controlling source",
    93: "Benziger93 lower-Office genitive differs from the controlling source",
    95: "Benziger95 final comma differs from the controlling source",
}


def assert_critical_clauses(corpus):
    lines = (corpus / checker.VIGIL_CHARTER).read_text(encoding="utf-8").splitlines()
    for number, reading in CRITICAL_CLAUSES.items():
        assert reading in lines, MESSAGES[number]


def copied(tmp_path):
    paths = set(checker.CHARTERS)
    paths.update(p for sources in checker.CHARTERS.values() for p in sources)
    for relative in paths:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    assert checker.charter(tmp_path) == []
    return tmp_path


def test_selected_source_readings_are_literal_not_only_article_numbers():
    assert_critical_clauses(ROOT)
    text = (ROOT / checker.VIGIL_CHARTER).read_text(encoding="utf-8")
    assert "a) vigilia Ascensionis Domini;" in text.splitlines()
    assert (
        "Vigilia Paschatis vero, cum non sit dies liturgicus, modo sibi proprio, "
        "seu pervigilio, celebratur."
    ) in text.splitlines()
    assert (
        "a) vigilia Nativitatis Domini quae, in occurrentia, locum tenet dominicae IV Adventus, "
        "de qua, proinde, nulla fit commemoratio;"
    ) in text.splitlines()
    assert (
        "Hae vigiliae praeferuntur diebus liturgicis III et IV classis; "
        "et, si impediuntur, commemorantur, iuxta rubricas."
    ) in text.splitlines()
    assert (
        "33. Vigilia II aut III classis penitus omittitur, si occurrat in dominica quavis, "
        "aut in festo I classis, vel si festum cui praemittitur in alium diem transferri "
        "aut ad commemorationem reduci contingat."
    ) in text.splitlines()
    assert (
        "34. Officium vigiliae incipit a Matutino et explicit quando initium habet Officium "
        "festi subsequentis."
    ) in text.splitlines()
    assert (
        "108. Commemorationes privilegiatae fiunt in Laudibus et in Vesperis necnon in omnibus "
        "Missis; commemorationes vero ordinariae fiunt tantum in Laudibus, in Missis "
        "conventualibus et in omnibus Missis lectis."
    ) in text.splitlines()
    assert "Omnes aliae commemorationes sunt commemorationes ordinariae." in text.splitlines()
    assert (
        "c) in aliis diebus liturgicis II classis, una tantum admittitur commemoratio, "
        "scilicet aut una privilegiata aut una ordinaria;"
    ) in text.splitlines()
    assert (
        "113. Commemoratio de Tempore fit primo loco. In admittendis et ordinandis aliis "
        "commemorationibus, servetur ordo tabellae praecedentiae."
    ) in text.splitlines()
    assert (
        "114. Quaelibet commemoratio, quae numerum pro singulis diebus liturgicis statutum "
        "superet, omittitur."
    ) in text.splitlines()
    assert (
        "96. Festum I classis impeditum a die qui in tabella praecedentiae superiorem obtinet "
        "locum, transfertur in proximum sequentem diem qui non sit I vel II classis."
    ) in text.splitlines()


@pytest.mark.parametrize("number", [28, 31, 32, 33, 96])
def test_new_cited_article_cannot_be_deleted_from_the_actual_extract(tmp_path, number):
    corpus = copied(tmp_path)
    path = corpus / checker.VIGIL_CHARTER
    before = path.read_bytes()
    lines = before.decode().splitlines(keepends=True)
    assert sum(line.startswith(f"{number}. ") for line in lines) == 1
    try:
        path.write_text(
            "".join(line for line in lines if not line.startswith(f"{number}. ")), encoding="utf-8"
        )
        name = "kalendarium/roman.py" if number == 96 else "kalendarium/temporale.py"
        sources = ", ".join(checker.CHARTERS[name])
        assert (f"{name} cites n. {number}, which {sources} does not print") in checker.charter(
            corpus
        )
    finally:
        path.write_bytes(before)
    assert checker.charter(corpus) == []


@pytest.mark.parametrize("place", [1, 2, 3, 4, 5, 6, 9, 15, 16, 21])
def test_selected_table_place_cannot_be_substituted_behind_article91(tmp_path, place):
    corpus = copied(tmp_path)
    path = corpus / checker.VIGIL_CHARTER
    before = path.read_bytes()
    try:
        path.write_bytes(before.replace(f"# table-place{place}:".encode(), b"# deleted-place:", 1))
        assert checker.charter(corpus) == [
            f"{checker.VIGIL_CHARTER}: missing selected precedence place {place}"
        ]
    finally:
        path.write_bytes(before)
    assert checker.charter(corpus) == []


def test_new_supplement_does_not_waive_the_old_article69_guard(tmp_path):
    corpus = copied(tmp_path)
    path = corpus / checker.CHARTER
    before = path.read_bytes()
    assert b"69. " in before
    try:
        path.write_bytes(
            b"".join(
                line for line in before.splitlines(keepends=True) if not line.startswith(b"69. ")
            )
        )
        assert any("cites n. 69," in error for error in checker.charter(corpus))
    finally:
        path.write_bytes(before)
    assert checker.charter(corpus) == []


def test_an_unknown_future_article_is_not_broadly_accepted(tmp_path):
    corpus = copied(tmp_path)
    path = corpus / "kalendarium/temporale.py"
    before = path.read_bytes()
    try:
        path.write_bytes(before + b"\n# n. 999\n")
        assert any("cites n. 999," in error for error in checker.charter(corpus))
    finally:
        path.write_bytes(before)
    assert checker.charter(corpus) == []


@pytest.mark.parametrize("number", [33, 93, 95])
def test_exact_controlling_clause_mutants_fail_and_recover_in_real_copied_source(tmp_path, number):
    corpus = copied(tmp_path)
    path = corpus / checker.VIGIL_CHARTER
    before = path.read_bytes()
    assert_critical_clauses(corpus)
    old, wrong = {
        33: (b"cui praemittitur", b"cui praemittuntur"),
        93: (b"per minus nobilis omissionem", b"per minus nobilem omissionem"),
        95: (b"locum, et aliud omittitur.", b"locum; et aliud omittitur."),
    }[number]
    assert before.count(old) == 1
    try:
        path.write_bytes(before.replace(old, wrong, 1))
        # Article presence still passes: this is a narrow literal source-oracle
        # test, not a false claim of a general Latin grammar/body validator.
        assert checker.charter(corpus) == []
        with pytest.raises(AssertionError, match=re.escape(MESSAGES[number])):
            assert_critical_clauses(corpus)
    finally:
        path.write_bytes(before)
    assert_critical_clauses(corpus)
    assert checker.charter(corpus) == []
