"""Punctuation in macro names never changes exact archived evidence or Latin."""

import hashlib
import json
from pathlib import Path

import pytest

from checks.raw_binding import BindingError, resolve_binding


def bound(monkeypatch, directive, *, section="Per Dominum", book=None):
    root = Path("/source-reference-test")
    revision = "4" * 40
    origin = "witnesses/raw/day.txt"
    prayer = "witnesses/raw/prayers.txt"
    witness = "witnesses/example/do.txt"
    source = f"[Postcommunio]\nQuǽsumus.\n{directive}\n".encode()
    formula = f"[{section}]\nr. Per Dóminum.\nR. Amen.\n".encode()
    registry = {
        "version": 1,
        "archives": {
            "day": {
                "upstream": "web/www/missa/Latin/Tempora/Pasc1-0.txt",
                "revision": revision,
                "path": origin,
                "sha256": hashlib.sha256(source).hexdigest(),
            },
            "prayers": {
                "upstream": book or "web/www/missa/Latin/Ordo/Prayers.txt",
                "revision": revision,
                "path": prayer,
                "sha256": hashlib.sha256(formula).hexdigest(),
            },
        },
        "bindings": {
            "example": {
                "witness": witness,
                "revision": revision,
                "evidence": [
                    {
                        "archive": "day",
                        "first": 2,
                        "last": 3,
                        "section": "Postcommunio",
                        "section_line": 1,
                    },
                    {
                        "archive": "prayers",
                        "first": 2,
                        "last": 3,
                        "section": section,
                        "section_line": 1,
                    },
                ],
                "references": [{"archive": "day", "line": 3, "text": directive, "target": 1}],
                "reading": [
                    {"archive": "day", "first": 2, "last": 2},
                    {"archive": "prayers", "first": 2, "last": 3},
                ],
            }
        },
    }
    header = (
        f"# revision: {revision}\n"
        "# path: web/www/missa/Latin/Tempora/Pasc1-0.txt "
        "[Postcommunio] (lines 2-3); "
        f"{registry['archives']['prayers']['upstream']} "
        f"[{section}] (lines 2-3)\n# raw-binding: example\n"
    )
    files = {
        root / origin: source,
        root / prayer: formula,
        root / witness: (header + "Quǽsumus. Per Dóminum. Amen.\n").encode(),
    }

    def save():
        files[root / "witnesses/raw/bindings.json"] = (json.dumps(registry) + "\n").encode()

    save()
    rb, rt, ex, isf = Path.read_bytes, Path.read_text, Path.exists, Path.is_file
    monkeypatch.setattr(Path, "read_bytes", lambda p: files[p] if p in files else rb(p))
    monkeypatch.setattr(
        Path, "read_text", lambda p, *a, **k: files[p].decode() if p in files else rt(p, *a, **k)
    )
    monkeypatch.setattr(Path, "exists", lambda p: p in files or ex(p))
    monkeypatch.setattr(Path, "is_file", lambda p: p in files or isf(p))
    return root, root / witness, registry, files, save


@pytest.mark.parametrize(
    "directive",
    [
        "$Per Dominum",
        "$Per Dominum.",
        "$Per. Dominum..",
        "&Per Dominum",
        "&Per Dominum.",
        "&Per. Dominum..",
    ],
)
def test_periods_are_removed_only_for_macro_destination_comparison(monkeypatch, directive):
    root, path, registry, files, _ = bound(monkeypatch, directive)
    before = dict(files)
    result = resolve_binding(path, root)
    assert result is not None and result.text == "Quǽsumus. Per Dóminum. Amen."
    assert result.source["binding"]["references"][0]["text"] == directive
    assert files == before
    assert result.source["archives"] == registry["archives"]


@pytest.mark.parametrize(
    "change",
    [
        "literal",
        "wrong-name",
        "wrong-target",
        "wrong-book",
        "hash",
        "read-reference",
        "omit-response",
        "omit-response-coherent-body",
        "accent",
        "comma",
        "extra-word",
        "delimiter",
        "removed-marker",
    ],
)
def test_dotted_macro_does_not_relax_other_source_boundaries(monkeypatch, change):
    root, path, registry, files, save = bound(monkeypatch, "$Per Dominum.")
    assert resolve_binding(path, root) is not None
    binding = registry["bindings"]["example"]
    if change == "literal":
        binding["references"][0]["text"] = "$Per Dominum"
    elif change == "wrong-name":
        binding["references"][0]["text"] = "$Qui vivis."
    elif change == "wrong-target":
        binding["references"][0]["target"] = 0
    elif change == "wrong-book":
        registry["archives"]["prayers"]["upstream"] = "web/www/horas/Latin/Ordo/Prayers.txt"
        files[path] = files[path].replace(
            b"web/www/missa/Latin/Ordo/Prayers.txt", b"web/www/horas/Latin/Ordo/Prayers.txt"
        )
    elif change == "hash":
        registry["archives"]["day"]["sha256"] = "0" * 64
    elif change == "read-reference":
        binding["reading"][0]["last"] = 3
    elif change == "omit-response":
        binding["reading"][1]["last"] = 2
    elif change == "omit-response-coherent-body":
        binding["reading"][1]["last"] = 2
        files[path] = files[path].replace(b" Amen.\n", b"\n")
    elif change == "accent":
        files[path] = files[path].replace("Dóminum".encode(), b"Dominum")
    elif change == "comma":
        files[path] = files[path].replace(b"Per ", b"Per, ")
    elif change == "extra-word":
        files[path] += b" Alienum.\n"
    elif change == "delimiter":
        binding["reading"][0]["first"] = 1
    else:
        files[path] = files[path].replace(b"# raw-binding: example\n", b"")
    save()
    with pytest.raises(BindingError):
        resolve_binding(path, root)


@pytest.mark.parametrize(
    "directive,section",
    [
        ("$Per Dominum,", "Per Dominum"),
        ("$Per Dominum;", "Per Dominum"),
        ("$Per Dominum!", "Per Dominum"),
        ("$Per Dominum:", "Per Dominum"),
        ("$Per Dominum…", "Per Dominum"),
        ("$Per Dominum.", "per Dominum"),
        ("$callpopup.", "callpopup"),
        ("$rubrics.", "rubrics"),
    ],
)
def test_no_general_punctuation_case_or_runtime_normalization(monkeypatch, directive, section):
    root, path, _, _, _ = bound(monkeypatch, directive, section=section)
    with pytest.raises(BindingError):
        resolve_binding(path, root)


@pytest.mark.parametrize(
    "directive,section", [("$Per Dominum.", "Aliud"), ("&Per Dominum.", "Aliud")]
)
def test_exact_but_wrong_destination_still_rejected(monkeypatch, directive, section):
    root, path, _, _, _ = bound(monkeypatch, directive, section=section)
    with pytest.raises(BindingError):
        resolve_binding(path, root)


@pytest.mark.parametrize(
    "directive,accepted",
    [
        ("$Per Dominum", True),
        ("$Per Dominum.", False),
        ("&Per Dominum", True),
        ("&Per Dominum.", False),
    ],
)
def test_horas_does_not_inherit_unproved_mass_punctuation_rule(monkeypatch, directive, accepted):
    root, path, registry, files, save = bound(monkeypatch, directive)
    pairs = [
        ("day", "web/www/horas/Latin/Sancti/02-02.txt"),
        ("prayers", "web/www/horas/Latin/Psalterium/Common/Prayers.txt"),
    ]
    for key, upstream in pairs:
        previous = registry["archives"][key]["upstream"]
        registry["archives"][key]["upstream"] = upstream
        files[path] = files[path].replace(previous.encode(), upstream.encode())
    save()
    if accepted:
        assert resolve_binding(path, root) is not None
    else:
        with pytest.raises(BindingError):
            resolve_binding(path, root)


@pytest.mark.parametrize("directive,accepted", [("@Ordo/Prayers", True), ("@Ordo/Prayers.", False)])
def test_at_file_references_are_not_period_normalized(monkeypatch, directive, accepted):
    root, path, _, _, _ = bound(monkeypatch, directive, section="Postcommunio")
    if accepted:
        assert resolve_binding(path, root) is not None
    else:
        with pytest.raises(BindingError):
            resolve_binding(path, root)
