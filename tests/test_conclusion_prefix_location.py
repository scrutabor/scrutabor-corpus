"""Identify the continued Monday prayer, not the next day's running head."""

import json
from copy import deepcopy
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TEXTS = (
    "proprium.ascensio-domini-postcommunio",
    "proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-postcommunio",
    "proprium.immaculatum-cor-beatae-mariae-virginis-collecta",
)
SECTION = (
    "Feria II post dominicam I Passionis, Postcommunio (Sacramenti tui); "
    "seventeen-word conclusion prefix"
)
PAGE = "https://archive.org/details/missale-romanum-1962/page/n202/mode/1up"
EVIDENCE = "38c3d082c3cf4e7f82f87cf9f87595e62e3765cb625c1305005f1435cc985774"


@pytest.fixture(scope="module")
def uses():
    graph = json.loads((ROOT / "bibliography/graph.json").read_text(encoding="utf-8"))
    return {row["id"]: row for row in graph["uses"]}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def assert_prefix(row):
    locator = row["locator"]
    require(locator["section"] == SECTION, "conclusion belongs to Monday")
    require(
        (locator["printed"], locator["scan"], locator["page_url"])
        == ("p. 123", "leaf n202 / PDF p. 203", PAGE),
        "conclusion page identity",
    )
    require(row["evidence_sha256"] == EVIDENCE, "conclusion original identity")


@pytest.mark.parametrize("text", TEXTS)
def test_prefix_locator_names_the_actual_prayer(uses, text):
    assert_prefix(uses[f"use.{text}.conclusion-prefix.mr1962"])


@pytest.mark.parametrize("text", TEXTS)
@pytest.mark.parametrize("defect", ("running-head", "page", "original"))
def test_incorrect_locator_is_rejected_and_restored(uses, text, defect):
    row = uses[f"use.{text}.conclusion-prefix.mr1962"]
    snapshot = deepcopy(row)
    assert_prefix(row)
    broken = deepcopy(row)
    if defect == "running-head":
        broken["locator"]["section"] = SECTION.replace("Feria II ", "Feria III ")
        diagnostic = "conclusion belongs to Monday"
    elif defect == "page":
        broken["locator"]["scan"] = "leaf n201 / PDF p. 202"
        diagnostic = "conclusion page identity"
    else:
        broken["evidence_sha256"] = "0" * 64
        diagnostic = "conclusion original identity"
    assert broken != row
    with pytest.raises(AssertionError, match=f"^{diagnostic}$"):
        assert_prefix(broken)
    assert_prefix(row)
    assert row == snapshot


def test_other_uses_do_not_reintroduce_the_running_head(uses):
    selected = [row for row in uses.values() if row.get("locator", {}).get("page_url") == PAGE]
    assert len(selected) >= len(TEXTS)
    wrong = "Feria III post dominicam I Passionis, Postcommunio"
    assert not [row["id"] for row in selected if wrong in row["locator"].get("section", "")]
