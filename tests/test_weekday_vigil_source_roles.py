"""Exact ordinary oration identities for the 26 weekday-Vigil dates.

The literal table is independent of the production binding/catalogue.  These
tests supplement, rather than replace, complete-resource and calendar tests.
"""

import copy
import json
from pathlib import Path

import pytest

from build_reader import store
from kalendarium import commemorationes as producer

ROOT = Path(store.__file__).resolve().parent.parent
ROLES = ("collecta", "secreta", "postcommunio")
UNDER = "under-weekday-vigil"
VIGIL = "vigilia-ascensionis"
BINDINGS = "kalendarium/ascension-vigil-orations.json"
SOURCE_ORATIONS = (
    (
        4,
        29,
        "sanctus-petrus-martyr",
        (
            ("proprium.sancti-petri-martyris-collecta", "proper"),
            ("proprium.sancti-petri-martyris-secreta", "proper"),
            ("proprium.sancti-petri-martyris-postcommunio", "proper"),
        ),
    ),
    (
        4,
        30,
        "sancta-catharina-senensis",
        (
            ("proprium.sanctae-catharinae-senensis-collecta", "proper"),
            ("proprium.sanctae-catharinae-senensis-secreta", "proper"),
            ("proprium.sanctae-catharinae-senensis-postcommunio", "proper"),
        ),
    ),
    (
        5,
        2,
        "sanctus-athanasius",
        (
            ("proprium.sancti-athanasii-collecta", "proper"),
            ("proprium.sancti-athanasii-secreta", "proper"),
            ("proprium.sancti-athanasii-postcommunio", "proper"),
        ),
    ),
    (
        5,
        3,
        "sancti-alexander-eventius-theodulus-et-iuvenalis",
        (
            ("proprium.sanctorum-alexandri-eventii-theoduli-et-iuvenalis-collecta", "proper"),
            ("proprium.super-has-hostias-secreta", "reference"),
            ("proprium.sanctorum-alexandri-eventii-theoduli-et-iuvenalis-postcommunio", "proper"),
        ),
    ),
    (
        5,
        4,
        "sancta-monica",
        (
            ("proprium.sanctae-monicae-collecta", "proper"),
            ("proprium.sanctae-petronillae-secreta", "reference"),
            ("proprium.sanctae-petronillae-postcommunio", "reference"),
        ),
    ),
    (
        5,
        5,
        "sanctus-pius-v",
        (
            ("proprium.sancti-pii-v-collecta", "proper"),
            ("proprium.oblatis-muneribus-secreta", "reference"),
            ("proprium.refectione-sancta-postcommunio", "reference"),
        ),
    ),
    (
        5,
        7,
        "sanctus-stanislaus",
        (
            ("proprium.sancti-stanislai-collecta", "proper"),
            ("proprium.sancti-stanislai-secreta", "proper"),
            ("proprium.sancti-stanislai-postcommunio", "proper"),
        ),
    ),
    (
        5,
        9,
        "sanctus-gregorius-nazianzenus",
        (
            ("proprium.sancti-gregorii-nazianzeni-collecta", "proper"),
            ("proprium.sancti-gregorii-nazianzeni-secreta", "proper"),
            ("proprium.sancti-gregorii-nazianzeni-postcommunio", "proper"),
        ),
    ),
    (
        5,
        10,
        "sanctus-antoninus",
        (
            ("proprium.sancti-antonini-collecta", "proper"),
            ("proprium.sancti-tui-secreta", "reference"),
            ("proprium.sancti-antonini-postcommunio", "proper"),
        ),
    ),
    (
        5,
        12,
        "sancti-nereus-achilleus-domitilla-et-pancratius",
        (
            ("proprium.sanctorum-nerei-achillei-domitillae-et-pancratii-collecta", "proper"),
            ("proprium.sanctorum-nerei-achillei-domitillae-et-pancratii-secreta", "proper"),
            ("proprium.sanctorum-nerei-achillei-domitillae-et-pancratii-postcommunio", "proper"),
        ),
    ),
    (
        5,
        13,
        "sanctus-robertus-bellarmino",
        (
            ("proprium.sancti-roberti-bellarmino-collecta", "proper"),
            ("proprium.sancti-roberti-bellarmino-secreta", "proper"),
            ("proprium.sancti-roberti-bellarmino-postcommunio", "proper"),
        ),
    ),
    (
        5,
        14,
        "sanctus-bonifatius-martyr",
        (
            ("proprium.sancti-bonifatii-martyris-collecta", "proper"),
            ("proprium.in-octava-nativitatis-secreta", "reference"),
            ("proprium.sancti-bonifatii-martyris-postcommunio", "proper"),
        ),
    ),
    (
        5,
        15,
        "sanctus-ioannes-baptista-de-la-salle",
        (
            ("proprium.sancti-ioannis-baptistae-de-la-salle-collecta", "proper"),
            ("proprium.laudis-tibi-secreta", "reference"),
            ("proprium.refecti-cibo-potuque-postcommunio", "reference"),
        ),
    ),
    (
        5,
        16,
        "sanctus-ubaldus",
        (
            ("proprium.sancti-ubaldi-collecta", "proper"),
            ("proprium.sancti-tui-secreta", "reference"),
            ("proprium.sancti-ubaldi-postcommunio", "proper"),
        ),
    ),
    (
        5,
        17,
        "sanctus-paschalis-baylon",
        (
            ("proprium.sancti-paschalis-baylon-collecta", "proper"),
            ("proprium.laudis-tibi-secreta", "reference"),
            ("proprium.refecti-cibo-potuque-postcommunio", "reference"),
        ),
    ),
    (
        5,
        18,
        "sanctus-venantius-martyr",
        (
            ("proprium.sancti-venantii-martyris-collecta", "proper"),
            ("proprium.sancti-venantii-martyris-secreta", "proper"),
            ("proprium.sancti-venantii-martyris-postcommunio", "proper"),
        ),
    ),
    (
        5,
        19,
        "sanctus-petrus-caelestinus",
        (
            ("proprium.sancti-petri-caelestini-collecta", "proper"),
            ("proprium.oblatis-muneribus-secreta", "reference"),
            ("proprium.refectione-sancta-postcommunio", "reference"),
        ),
    ),
    (
        5,
        20,
        "sanctus-bernardinus-senensis",
        (
            ("proprium.sancti-bernardini-senensis-collecta", "proper"),
            ("proprium.laudis-tibi-secreta", "reference"),
            ("proprium.refecti-cibo-potuque-postcommunio", "reference"),
        ),
    ),
    (
        5,
        25,
        "sanctus-gregorius-vii",
        (
            ("proprium.sancti-gregorii-vii-collecta", "proper"),
            ("proprium.oblatis-muneribus-secreta", "reference"),
            ("proprium.refectione-sancta-postcommunio", "reference"),
        ),
    ),
    (
        5,
        26,
        "sanctus-philippus-nerius",
        (
            ("proprium.sancti-philippi-nerii-collecta", "proper"),
            ("proprium.sancti-philippi-nerii-secreta", "proper"),
            ("proprium.sancti-philippi-nerii-postcommunio", "proper"),
        ),
    ),
    (
        5,
        27,
        "sanctus-beda-venerabilis",
        (
            ("proprium.sancti-bedae-venerabilis-collecta", "proper"),
            ("proprium.sancti-bedae-venerabilis-secreta", "proper"),
            ("proprium.sancti-bedae-venerabilis-postcommunio", "proper"),
        ),
    ),
    (
        5,
        28,
        "sanctus-augustinus-cantuariensis",
        (
            ("proprium.sancti-augustini-cantuariensis-collecta", "proper"),
            ("proprium.sancti-augustini-cantuariensis-secreta", "proper"),
            ("proprium.sancti-augustini-cantuariensis-postcommunio", "proper"),
        ),
    ),
    (
        5,
        29,
        "sancta-maria-magdalena-de-pazzis",
        (
            ("proprium.sanctae-mariae-magdalenae-de-pazzis-collecta", "proper"),
            ("proprium.sanctae-petronillae-secreta", "reference"),
            ("proprium.sanctae-petronillae-postcommunio", "reference"),
        ),
    ),
    (
        5,
        30,
        "sanctus-felix-i-papa",
        (
            ("proprium.sancti-felicis-i-papae-collecta", "proper"),
            ("proprium.oblatis-muneribus-secreta", "reference"),
            ("proprium.refectione-sancta-postcommunio", "reference"),
        ),
    ),
    (
        6,
        1,
        "sancta-angela-mericia",
        (
            ("proprium.sanctae-angelae-mericiae-collecta", "proper"),
            ("proprium.sanctae-angelae-mericiae-secreta", "proper"),
            ("proprium.sanctae-angelae-mericiae-postcommunio", "proper"),
        ),
    ),
    (
        6,
        2,
        "sancti-marcellinus-petrus-et-erasmus",
        (
            ("proprium.sanctorum-marcellini-petri-et-erasmi-collecta", "proper"),
            ("proprium.haec-hostia-secreta", "reference"),
            ("proprium.sacro-munere-postcommunio", "reference"),
        ),
    ),
)


def assert_source_roles(binding, docs):
    """Check the literal oracle, not just agreement between two producers."""
    assert set(binding) == {"schema_version", "vigil", "routes"}
    assert binding["schema_version"] == "1.0.0" and binding["vigil"] == VIGIL
    assert type(binding["routes"]) is list and len(binding["routes"]) == 26
    lower = [d for d in docs if d.get("occurrence", {}).get("kind") == UNDER]
    assert len(lower) == 26
    assert {d["id"] for d in lower} == {r[2] for r in SOURCE_ORATIONS}
    for index, (month, day, identity, selected) in enumerate(SOURCE_ORATIONS):
        message = f"source-role oracle {month:02d}-{day:02d} {identity}"
        route = binding["routes"][index]
        assert set(route) == {"month", "day", "commemoration", "orations"}, message
        assert type(route["month"]) is int and type(route["day"]) is int, message
        assert (route["month"], route["day"], route["commemoration"]) == (month, day, identity), (
            message
        )
        assert route["orations"] == {role: selected[i][0] for i, role in enumerate(ROLES)}, message
        found = [d for d in lower if d["id"] == identity]
        assert len(found) == 1, message
        doc = found[0]
        rule = doc["occurrence"]
        assert type(rule["month"]) is int and type(rule["day"]) is int, message
        assert rule == {"kind": UNDER, "vigil": VIGIL, "month": month, "day": day}, message
        assert [s["key"] for s in doc["slots"]] == list(ROLES), message
        assert [(s["text"], s["relation"]) for s in doc["slots"]] == list(selected), message


def actual_inputs():
    return json.loads((ROOT / BINDINGS).read_bytes()), producer.authored(ROOT)


def coordinated(binding, docs, index, replacements):
    """Damage both stored sources consistently, leaving the oracle untouched."""
    bad_binding, bad_docs = copy.deepcopy((binding, docs))
    route = bad_binding["routes"][index]
    doc = next(d for d in bad_docs if d["id"] == route["commemoration"])
    for role, target in replacements.items():
        route["orations"][role] = target
        next(s for s in doc["slots"] if s["key"] == role)["text"] = target
    assert route["orations"] == {s["key"]: s["text"] for s in doc["slots"]}
    return bad_binding, bad_docs


def test_all_26_source_selected_oration_triples():
    assert len(SOURCE_ORATIONS) == 26
    assert sum(len(row[3]) for row in SOURCE_ORATIONS) == 78
    assert_source_roles(*actual_inputs())


def test_coordinated_wrong_role_swaps_fail_and_recover():
    binding, docs = actual_inputs()
    before = json.dumps([binding, docs], ensure_ascii=False, separators=(",", ":"))
    assert_source_roles(binding, docs)
    for index, (month, day, _identity, selected) in enumerate(SOURCE_ORATIONS):
        bad = coordinated(
            binding, docs, index, {"collecta": selected[1][0], "secreta": selected[0][0]}
        )
        with pytest.raises(AssertionError, match=f"source-role oracle {month:02d}-{day:02d}"):
            assert_source_roles(*bad)
        assert_source_roles(binding, docs)
    assert json.dumps([binding, docs], ensure_ascii=False, separators=(",", ":")) == before


def test_coordinated_wrong_target_for_every_role_fails_and_recovers():
    binding, docs = actual_inputs()
    before = json.dumps([binding, docs], ensure_ascii=False, separators=(",", ":"))
    assert_source_roles(binding, docs)
    checked = []
    for index, (month, day, _identity, selected) in enumerate(SOURCE_ORATIONS):
        for slot, role in enumerate(ROLES):
            foreign = next(
                row[3][slot][0] for row in SOURCE_ORATIONS if row[3][slot][0] != selected[slot][0]
            )
            bad = coordinated(binding, docs, index, {role: foreign})
            with pytest.raises(AssertionError, match=f"source-role oracle {month:02d}-{day:02d}"):
                assert_source_roles(*bad)
            assert_source_roles(binding, docs)
            checked.append((month, day, role))
    assert len(checked) == len(set(checked)) == 78
    assert json.dumps([binding, docs], ensure_ascii=False, separators=(",", ":")) == before
