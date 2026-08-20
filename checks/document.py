"""What a document claims about ITSELF, held against what it is.

Four fields describe a text rather than carry it — its id, its category, the
section of the book it stands in, and whether it is sung — and a census of
unguarded mutations (2026-08-19) found every one of them free. A file at
`texts/ordinarium/credo.json` could call itself `orationes.pater-noster` and
the suite stayed green, because every check downstream believes the field: the
id is half of every word's external address (checks/addresses.py), the app's
routes are built from the category, and `section` and `sung` are read as
enumerations by code that never sees an unexpected value coming.

The declared path to a text's witnesses is the same shape of claim. It reads
like the thing the collation follows, and it is not: the witness directory is
DERIVED from the text id everywhere it is used, so pointing `source.witnesses`
at another text's folder changed nothing and reported nothing. A line that
looks like provenance and is only decoration is worse than no line, so it must
say what the corpus actually does.

The vocabularies below are the values the corpus uses today, written down.
Adding a section or a category is a line here, which is the house pattern for
every other ruling: data, and never silent.
"""

from __future__ import annotations

from pathlib import Path

# The directories under texts/, which are also the first half of every text id.
CATEGORIES = frozenset(("defunctorum", "litaniae", "orationes", "ordinarium", "proprium", "psalmi"))

# Where a text stands in the book. The Mass is divided as the Missale divides
# it; the rest name their own shelf.
SECTIONS = frozenset(
    (
        "praeparatio",
        "missa-catechumenorum",
        "missa-fidelium",
        "orationes-communes",
        "orationes-pro-defunctis",
        "litaniae-approbatae",
        "psalmus-118",
    )
)

# JSON true or false — not the strings, and not 1 and 0. The reader's Mass-form
# picker branches on this, so a truthy string would read as sung everywhere.
SUNG = frozenset((True, False))


def check(doc: dict, path: Path) -> list[str]:
    """The document against its own file, and against the vocabularies."""
    errors: list[str] = []
    name = path.stem
    category = path.parent.name
    expected = f"{category}.{name}"
    declared = doc.get("id")
    if declared != expected:
        errors.append(
            f"{path.parent.name}/{path.name}: calls itself {declared!r}, and its path says "
            f"{expected!r} — the id is half of every word's address and is read from the "
            f"file it is stored in"
        )
    if doc.get("category") != category:
        errors.append(
            f"{expected}: category={doc.get('category')!r} but the text is stored under "
            f"{category!r}"
        )
    if category not in CATEGORIES:
        errors.append(
            f"{expected}: {category!r} is not a declared category — name it in "
            f"checks/document.py, or the text is in the wrong directory"
        )
    section = doc.get("section")
    if section not in SECTIONS:
        errors.append(
            f"{expected}: section={section!r} is not one of the sections this book has "
            f"({', '.join(sorted(SECTIONS))})"
        )
    sung = doc.get("sung")
    if not isinstance(sung, bool) or sung not in SUNG:
        errors.append(
            f"{expected}: sung={sung!r} — sung is JSON true or false, and the reader's "
            f"Mass-form picker branches on it"
        )

    source = (doc.get("editorial") or {}).get("source") or {}
    text_id = declared if isinstance(declared, str) else expected
    for key, derived in (
        ("witnesses", f"witnesses/{text_id}/"),
        ("apparatus", f"witnesses/{text_id}/apparatus.json"),
    ):
        if key in source and source[key] != derived:
            errors.append(
                f"{text_id}: source.{key} declares {source[key]!r}, and the collation reads "
                f"{derived!r} — the path is derived from the text id, so a declaration that "
                f"disagrees with it is read by nobody"
            )

    # The pointer's other half (SCHEMA.md: a pointer to no file is also an
    # error). The derived-path rule above holds the NAME; this holds the
    # thing named, in both directions: a declaration must have its file, and
    # an apparatus that exists must be declared (owner ruling, 2026-08-20).
    apparatus = path.parents[2] / "witnesses" / text_id / "apparatus.json"
    if "apparatus" in source and not apparatus.exists():
        errors.append(
            f"{text_id}: source.apparatus names a file that does not exist — a pointer "
            f"to nothing reads like provenance and is only decoration"
        )
    if apparatus.exists() and "apparatus" not in source:
        errors.append(
            f"{text_id}: witnesses/{text_id}/apparatus.json exists and source.apparatus "
            f"does not name it — an apparatus nobody declares cannot be followed"
        )
    return errors
