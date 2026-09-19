"""A witness must be findable in the archive it names."""

from pathlib import Path

from checks.witness_archive import check, normalise


def build(tmp_path: Path, header: str, body: str, archives: dict[str, str]) -> Path:
    raw = tmp_path / "witnesses" / "raw"
    raw.mkdir(parents=True)
    for name, text in archives.items():
        (raw / name).write_text(text)
    d = tmp_path / "witnesses" / "ordinarium.x"
    d.mkdir(parents=True)
    (d / "do.txt").write_text(header + "\n" + body)
    return tmp_path


def test_the_cross_is_printed_inside_the_word():
    # Divinum Officium prints "bene + dícas"; a naive split loses the word
    assert "benedícas" in normalise("uti accépta hábeas et bene + dícas")


def test_inline_rubrics_are_stripped_before_comparing():
    assert normalise("rogámus (osculatur Altare) ac pétimus") == "rogámus ac pétimus".lower()


def test_a_contained_witness_passes(tmp_path):
    root = build(
        tmp_path,
        "# fetched: 2026 (archived at ../raw/src.txt)",
        "Te ígitur clementíssime Pater",
        {"src.txt": "v. Te ígitur, clementíssime Pater, per Jesum Christum"},
    )
    assert check(root) == []


def test_a_witness_from_another_archive_fails(tmp_path):
    root = build(
        tmp_path,
        "# fetched: 2026 (archived at ../raw/src.txt)",
        "Commúnicantes et memóriam venerántes in primis gloriósæ",
        {"src.txt": "v. Te ígitur, clementíssime Pater"},
    )
    errors = check(root)
    assert errors and "not in the archive it names" in errors[0]


def test_naming_two_archives_pools_them(tmp_path):
    root = build(
        tmp_path,
        "# fetched: 2026 (archived at ../raw/a.txt and ../raw/b.txt)",
        "Te ígitur Commúnicantes",
        {"a.txt": "Te ígitur", "b.txt": "Commúnicantes"},
    )
    assert check(root) == []


def test_an_archive_that_does_not_exist_is_an_error(tmp_path):
    root = build(
        tmp_path,
        "# fetched: 2026 (archived at ../raw/gone.txt)",
        "Te ígitur",
        {"src.txt": "Te ígitur"},
    )
    errors = check(root)
    assert errors and "do not exist" in errors[0]


def test_one_missing_word_in_a_long_witness_is_not_tolerated(tmp_path):
    root = build(
        tmp_path, "# archived: ../raw/src.txt", "Deus " * 122 + "alienum", {"src.txt": "Deus"}
    )
    assert "1 of 123 words" in check(root)[0]


def test_a_substring_does_not_attest_a_whole_word(tmp_path):
    root = build(tmp_path, "# archived: ../raw/src.txt", "sum", {"src.txt": "sumus"})
    assert check(root)


def test_a_repository_relative_archive_is_checked(tmp_path):
    root = build(tmp_path, "# local-archive: witnesses/raw/src.txt", "alienum", {"src.txt": "Deus"})
    assert check(root)


def test_a_late_header_reference_is_not_ignored(tmp_path):
    root = build(
        tmp_path,
        "# note: context\n" * 21 + "# archived: ../raw/src.txt",
        "alienum",
        {"src.txt": "Deus"},
    )
    assert check(root)


def test_crosses_can_also_stand_between_whole_words(tmp_path):
    root = build(
        tmp_path,
        "# archived: ../raw/src.txt",
        "Hóstiam puram benedícas",
        {"src.txt": "Hóstiam + puram bene + dícas"},
    )
    assert check(root) == []


def test_accented_ligatures_remain_whole_letters():
    assert normalise("sǽcula quǽsumus") == "sǽcula quǽsumus"


def test_an_empty_bound_witness_cannot_pass(tmp_path):
    root = build(tmp_path, "# archived: ../raw/src.txt", "", {"src.txt": "Deus"})
    assert "no words" in check(root)[0]


def test_optional_alleluia_requires_the_witness_declaration(tmp_path):
    root = build(
        tmp_path,
        "# archived: ../raw/src.txt",
        "Deus Allelúja.",
        {"src.txt": "Deus (Allelúja.) (rubrica)."},
    )
    assert check(root)
    witness = root / "witnesses/ordinarium.x/do.txt"
    witness.write_text("# archived: ../raw/src.txt\n# seasonal-alleluia: include\nDeus Allelúja.")
    assert check(root) == []
    witness.write_text(witness.read_text() + " rubrica")
    assert check(root)


def test_archive_check_rejects_an_unknown_seasonal_declaration(tmp_path):
    root = build(
        tmp_path,
        "# archived: ../raw/src.txt\n# seasonal-alleluia: perhaps",
        "Deus",
        {"src.txt": "Deus"},
    )
    assert "seasonal-alleluia" in check(root)[0]
