"""Citation consistency is a separate gate from transcription correctness."""

import json
from pathlib import Path

import pytest

from build_reader.bibliography import _archive_locator

CORPUS = Path(__file__).resolve().parent.parent
BASE = "https://archive.org/details/missale-romanum-1962"


@pytest.mark.parametrize(
    ("url", "scan", "error"),
    [
        (BASE + "/page/n507/mode/1up", "leaf n507 / PDF p. 508", None),
        (BASE + "/page/n507/mode/1up", "leaves n507–n508 / PDF pp. 508–509", None),
        (BASE + "/page/n506/mode/1up", "leaf n507 / PDF p. 508", "leaf differs"),
        (BASE.replace("details", "download") + "/page/n507", "leaf n507", "use /details/"),
        (
            BASE.replace("missale-romanum", "missale_romanum") + "/page/n507",
            "leaf n507",
            "item differs",
        ),
    ],
)
def test_reader_links_must_identify_the_cited_item_and_leaf(url, scan, error):
    errors = []
    _archive_locator({"record_url": BASE}, {"page_url": url, "scan": scan}, "locator", errors)
    if error:
        assert any(error in value for value in errors)
    else:
        assert errors == []


def test_checked_andrew_page_keeps_the_printed_and_image_page_distinct():
    graph = json.loads((CORPUS / "bibliography/graph.json").read_text())
    item = next(
        i for i in graph["digital_items"] if i["id"] == "item.missale-romanum.1962-typica.ia"
    )
    assert item["record_url"] == BASE
    assert item["scan_url"].endswith("/Missale%20Romanum%201962.pdf")
    use = next(
        u
        for u in graph["uses"]
        if u["id"] == "use.proprium.sancti-andreae-apostoli-epistola.mr1962"
    )
    assert use["locator"] == {
        "printed": "p. 426",
        "scan": "leaf n507 / PDF p. 508",
        "page_url": BASE + "/page/n507/mode/1up",
    }
