import json

from checks.apparatus import derived_summary, lint_apparatus_summary, write_summaries


def test_summary_is_derived_from_entry_count_and_classes():
    apparatus = {
        "adjudicated": [
            {"at": "w001", "class": "punctuation"},
            {"at": "w002", "class": "orthography"},
            {"at": "w003", "class": "punctuation"},
        ]
    }
    assert derived_summary(apparatus) == {
        "entries": 3,
        "classes": ["orthography", "punctuation"],
    }


def test_stale_summary_fails(tmp_path):
    path = tmp_path / "apparatus.json"
    path.write_text(
        json.dumps(
            {
                "summary": {"entries": 1, "classes": ["punctuation"]},
                "adjudicated": [
                    {"at": "w001", "class": "punctuation"},
                    {"at": "w002", "class": "accent"},
                ],
            }
        ),
        encoding="utf-8",
    )
    errors = lint_apparatus_summary(path)
    assert len(errors) == 1
    assert "expected {'entries': 2, 'classes': ['accent', 'punctuation']}" in errors[0]


def test_missing_apparatus_has_nothing_to_summarize(tmp_path):
    assert lint_apparatus_summary(tmp_path / "apparatus.json") == []


def test_writer_places_the_derived_summary_beside_the_note(tmp_path):
    path = tmp_path / "witnesses" / "ordination.test" / "apparatus.json"
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "text": "ordination.test",
                "note": "Context that arithmetic cannot express.",
                "adjudicated": [{"at": "w001", "class": "accent"}],
            }
        ),
        encoding="utf-8",
    )
    assert write_summaries(tmp_path) == 1
    updated = json.loads(path.read_text(encoding="utf-8"))
    assert list(updated) == ["text", "note", "summary", "adjudicated"]
    assert updated["summary"] == {"entries": 1, "classes": ["accent"]}
    assert write_summaries(tmp_path) == 0
