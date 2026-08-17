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
