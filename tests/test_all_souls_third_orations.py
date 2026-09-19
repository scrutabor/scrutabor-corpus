"""The third All Souls Mass has its own, general intercessions."""

import json
from pathlib import Path

import pytest

from checks.normalize import substantive

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "commemoratio-omnium-fidelium-defunctorum-missa-iii-"
BODIES = {
    "collecta": (
        "Deus, véniæ largítor, et humánæ salútis amátor: quǽsumus cleméntiam "
        "tuam; ut ánimas famulórum famularúmque tuárum, quæ ex hoc sǽculo "
        "transiérunt, beáta María semper Vírgine intercedénte cum ómnibus "
        "Sanctis tuis, ad perpétuæ beatitúdinis consórtium perveníre concédas."
    ),
    "secreta": (
        "Deus, cuius misericórdiæ non est númerus, súscipe propítius preces "
        "humilitátis nostræ: et animábus ómnium fidélium defunctórum, quibus "
        "tui nóminis dedísti confessiónem, per hæc sacraménta salútis nostræ, "
        "cunctórum remissiónem tríbue peccatórum."
    ),
    "postcommunio": (
        "Præsta, quǽsumus, omnípotens et miséricors Deus: ut ánimæ famulórum "
        "famularúmque tuárum, pro quibus hoc sacrifícium laudis tuæ obtúlimus "
        "maiestáti; per huius virtútem sacraménti a peccátis ómnibus expiátæ, "
        "lucis perpétuæ, te miseránte, recípiant beatitúdinem."
    ),
}


def core(kind):
    return json.loads((ROOT / "texts/proprium" / f"{PREFIX}{kind}.json").read_text())


def words(kind):
    return {w["id"]: w for s in core(kind)["segments"] for w in s["words"]}


@pytest.mark.parametrize("kind", BODIES)
def test_proper_body_matches_third_mass_in_typical_edition(kind):
    # Printed pp. 726–727, not the similarly named prayers for relatives.
    tokens = core(kind)["segments"][0]["words"]
    end = next(i for i, w in enumerate(tokens) if w["form"] == "Per")
    actual = " ".join(w["form"] + w.get("post", "") for w in tokens[:end])
    assert substantive(actual) == substantive(BODIES[kind])


@pytest.mark.parametrize(
    "kind,retired",
    [
        ("collecta", range(12, 18)),
        ("secreta", range(14, 19)),
        ("postcommunio", range(9, 14)),
    ],
)
def test_removed_beneficiary_words_keep_safe_addresses(kind, retired):
    doc = core(kind)
    live = words(kind)
    for number in retired:
        wid = f"w{number:03}"
        assert wid not in live
        assert doc["ids"]["retired"][wid] == "s01"


def test_collect_addresses_god_and_marys_intercession_is_ablative():
    ws = words("collecta")
    for wid in ("w001", "w003", "w007"):
        assert ws[wid]["morph"]["case"] == "voc"
    for wid in ("w023", "w024", "w026", "w027"):
        assert ws[wid]["morph"]["case"] == "abl"
    assert ws["w018"]["morph"] == {
        "pos": "pron",
        "case": "nom",
        "number": "pl",
        "gender": "f",
    }


def test_postcommunion_souls_are_subject_and_majesty_is_the_recipient():
    ws = words("postcommunio")
    assert ws["w008"]["morph"]["case"] == "nom"
    assert ws["w008"]["morph"]["number"] == "pl"
    assert ws["w019"]["morph"]["case"] == "dat"
    assert ws["w019"]["head"] == "w021"
    assert ws["w029"]["head"] == "w008"
    assert ws["w033"]["morph"]["gender"] == "m"


def test_secret_mercy_is_genitive_not_dative():
    ws = words("secreta")
    assert ws["w003"]["morph"]["case"] == "gen"
    assert ws["w026"]["morph"]["number"] == "pl"
