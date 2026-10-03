"""Every Proper text names the 1962 Missal page that prints it.

The reader shows a Proper text's sources from its normalized uses. A text without a
Missal use shows none, which is how the Advent chants and readings went without sources
after the legacy citations were withdrawn for direct verification.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MISSAL = "edition.missale-romanum.1962-typica"
PRINTS = {"official_text", "direct_approved_print"}


def graph():
    return json.loads((ROOT / "bibliography/graph.json").read_text())


def propers():
    return sorted(f"proprium.{p.stem}" for p in (ROOT / "texts/proprium").glob("*.json"))


def printed(uses):
    return {
        u["address"].get("text")
        for u in uses
        if u["edition"] == MISSAL and u["role"] in PRINTS and u["address"]["kind"] == "text"
    }


def test_every_proper_text_has_a_missal_page():
    missing = [t for t in propers() if t not in printed(graph()["uses"])]
    assert missing == []
    assert len(propers()) > 900


def test_the_check_sees_a_text_without_its_page():
    text = "proprium.dominica-i-adventus-introitus"
    uses = [u for u in graph()["uses"] if u["address"].get("text") != text]
    assert text not in printed(uses)


def test_missal_page_locators_name_their_leaf():
    seen = 0
    for use in graph()["uses"]:
        locator = use["locator"]
        first = re.match(r"leaves? (n\d+)", locator.get("scan", ""))
        if use["edition"] != MISSAL or not first or "page_url" not in locator:
            continue
        assert f"/page/{first[1]}/" in locator["page_url"], use["id"]
        seen += 1
    assert seen > 40
