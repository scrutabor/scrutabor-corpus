"""English proper-orations register, short captions and ritual divisions."""

import hashlib
import json
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path

import pytest

from checks import interlinear

ROOT = Path(__file__).resolve().parents[1]

TRANSLATIONS: dict[str, dict[str, str]] = {
    "proprium.assumptio-beatae-mariae-virginis-secreta": {
        "s01": "May the offering of our "
        "devotion rise to You, "
        "Lord, and through the "
        "intercession of the "
        "most Blessed Virgin "
        "Mary, assumed into "
        "heaven, may our hearts, "
        "kindled with the fire "
        "of love, continually "
        "reach toward You. "
        "Through our Lord Jesus "
        "Christ, Your Son, who "
        "lives and reigns with "
        "You in the unity of the "
        "Holy Spirit, God,",
        "s02": "forever and ever.",
        "s03": "Amen.",
    },
    "proprium.corporis-christi-collecta": {
        "s01": "O God, who have left us under a "
        "wondrous sacrament the memorial of "
        "Your Passion, grant us, we pray, so to "
        "venerate the sacred mysteries of Your "
        "Body and Blood that we may continually "
        "experience within us the fruit of Your "
        "redemption. You live and reign with "
        "God the Father in the unity of the "
        "Holy Spirit, God, forever and ever.",
        "s02": "Amen.",
    },
    "proprium.corporis-christi-secreta": {
        "s01": "Graciously grant, we pray, Lord, to "
        "Your Church the gifts of unity and "
        "peace which are mystically signified "
        "under the offered gifts. Through our "
        "Lord Jesus Christ, Your Son, who lives "
        "and reigns with You in the unity of the "
        "Holy Spirit, God,",
        "s02": "forever and ever.",
        "s03": "Amen.",
    },
    "proprium.corporis-christi-postcommunio": {
        "s01": "Grant, we pray, Lord, that we may "
        "be filled with the eternal "
        "enjoyment of Your divinity, an "
        "enjoyment foreshadowed by our "
        "reception in time of Your precious "
        "Body and Blood. You live and reign "
        "with God the Father in the unity "
        "of the Holy Spirit, God, forever "
        "and ever.",
        "s02": "Amen.",
    },
    "proprium.dominica-ii-post-pentecosten-secreta": {
        "s01": "May the offering to be "
        "dedicated to Your name, "
        "Lord, purify us and day by "
        "day lead us to a heavenly "
        "way of life. Through our "
        "Lord Jesus Christ, Your "
        "Son, who lives and reigns "
        "with You in the unity of "
        "the Holy Spirit, God,",
        "s02": "forever and ever.",
        "s03": "Amen.",
    },
    "proprium.sacratissimi-cordis-iesu-collecta": {
        "s01": "O God, who are mercifully "
        "pleased to bestow on us the "
        "infinite treasures of love in "
        "Your Son’s Heart, wounded by "
        "our sins, grant, we pray, "
        "that, as we offer Him our "
        "devoted worship, we may also "
        "fulfill the duty of worthy "
        "reparation. Through the same "
        "Jesus Christ, our Lord, Your "
        "Son, who lives and reigns with "
        "You in the unity of the Holy "
        "Spirit, God, forever and ever.",
        "s02": "Amen.",
    },
    "proprium.sacratissimi-cordis-iesu-secreta": {
        "s01": "Look, we pray, Lord, upon the "
        "ineffable charity of the Heart "
        "of Your beloved Son, that what "
        "we offer may be an acceptable "
        "gift to You and an expiation "
        "for our sins. Through the same "
        "Jesus Christ, our Lord, Your "
        "Son, who lives and reigns with "
        "You in the unity of the Holy "
        "Spirit, God,",
        "s02": "forever and ever.",
        "s03": "Amen.",
    },
    "proprium.sacratissimi-cordis-iesu-postcommunio": {
        "s01": "May Your holy gifts, Lord "
        "Jesus, bestow divine "
        "fervor on us so that, "
        "having tasted the "
        "sweetness of Your most "
        "sweet Heart, we may learn "
        "to despise earthly things "
        "and love heavenly things. "
        "You live and reign with "
        "God the Father in the "
        "unity of the Holy Spirit, "
        "God, forever and ever.",
        "s02": "Amen.",
    },
    "proprium.sancti-bartholomaei-apostoli-collecta": {
        "s01": "Almighty, eternal God, who "
        "have given us the devout "
        "and holy joy of this day "
        "on the feast of Your "
        "blessed Apostle "
        "Bartholomew, grant to Your "
        "Church, we pray, both to "
        "love what he believed and "
        "to preach what he taught. "
        "Through our Lord Jesus "
        "Christ, Your Son, who "
        "lives and reigns with You "
        "in the unity of the Holy "
        "Spirit, God, forever and "
        "ever.",
        "s02": "Amen.",
    },
    "proprium.sancti-matthiae-apostoli-collecta": {
        "s01": "O God, who joined blessed "
        "Matthias to the company of "
        "Your Apostles, grant, we pray, "
        "that through his intercession "
        "we may always experience the "
        "tenderness of Your mercy "
        "toward us. Through our Lord "
        "Jesus Christ, Your Son, who "
        "lives and reigns with You in "
        "the unity of the Holy Spirit, "
        "God, forever and ever.",
        "s02": "Amen.",
    },
}

WORD_COUNTS: dict[str, int] = {
    "proprium.assumptio-beatae-mariae-virginis-secreta": 46,
    "proprium.corporis-christi-collecta": 46,
    "proprium.corporis-christi-secreta": 38,
    "proprium.corporis-christi-postcommunio": 35,
    "proprium.dominica-ii-post-pentecosten-secreta": 39,
    "proprium.sacratissimi-cordis-iesu-collecta": 53,
    "proprium.sacratissimi-cordis-iesu-secreta": 44,
    "proprium.sacratissimi-cordis-iesu-postcommunio": 37,
    "proprium.sancti-bartholomaei-apostoli-collecta": 50,
    "proprium.sancti-matthiae-apostoli-collecta": 42,
}

CAPTIONS: dict[str, dict[str, str]] = {
    "proprium.assumptio-beatae-mariae-virginis-secreta": {"w001": "May rise", "w025": "Through"},
    "proprium.corporis-christi-secreta": {"w001": "To Your Church"},
    "proprium.corporis-christi-postcommunio": {"w001": "Grant"},
    "proprium.dominica-ii-post-pentecosten-secreta": {
        "w001": "Sacrifice",
        "w006": "to be dedicated",
        "w018": "Through",
    },
    "proprium.sacratissimi-cordis-iesu-postcommunio": {"w001": "May bestow"},
    "proprium.sancti-matthiae-apostoli-collecta": {"w021": "Through"},
}

ABOUTS: dict[str, str] = {
    "proprium.corporis-christi-collecta": "The Collect of the feast of the Most Holy Body "
    "of Christ. It asks that we so venerate the "
    "sacred mysteries of the Lord’s Body and Blood "
    "that we continually experience within us the "
    "fruit of His redemption.",
    "proprium.corporis-christi-postcommunio": "The Postcommunion of the feast of the Most "
    "Holy Body of Christ. It asks that we be "
    "filled with the eternal enjoyment of "
    "Christ’s divinity, an enjoyment "
    "foreshadowed by our temporal reception of "
    "His precious Body and Blood.",
}

PROSE_PREDECESSORS: list[tuple[str, str, str]] = [
    (
        "proprium.assumptio-beatae-mariae-virginis-secreta",
        "s01",
        "May the offering of our devotion rise unto You, O Lord, and by the intercession of "
        "the most Blessed Virgin Mary, who was taken up into heaven, may our hearts, on fire "
        "with love, strive ever upward to You. Through our Lord Jesus Christ, Thy Son, who "
        "liveth and reigneth with Thee in the unity of the Holy Ghost, God,",
    ),
    ("proprium.assumptio-beatae-mariae-virginis-secreta", "s02", "world without end."),
    (
        "proprium.corporis-christi-collecta",
        "s01",
        "O God, who hast left us under a wondrous Sacrament the memorial of Thy Passion, "
        "grant us, we beseech Thee, so to venerate the sacred mysteries of Thy Body and "
        "Blood that we may continually feel within us the fruit of Thy redemption, who "
        "livest and reignest with God the Father in the unity of the Holy Ghost, God, world "
        "without end.",
    ),
    (
        "proprium.corporis-christi-secreta",
        "s01",
        "Graciously grant, we beseech Thee, O Lord, to Thy Church the gifts of unity and "
        "peace which are mystically signified beneath the offerings presented. Through our "
        "Lord Jesus Christ, Thy Son, who liveth and reigneth with Thee in the unity of the "
        "Holy Ghost, God,",
    ),
    ("proprium.corporis-christi-secreta", "s02", "world without end."),
    (
        "proprium.corporis-christi-postcommunio",
        "s01",
        "Grant, we beseech Thee, O Lord, that we may be filled with the everlasting "
        "enjoyment of Thy Godhead, which is foreshadowed by the temporal reception of Thy "
        "precious Body and Blood, who livest and reignest with God the Father in the unity "
        "of the Holy Ghost, God, world without end.",
    ),
    (
        "proprium.dominica-ii-post-pentecosten-secreta",
        "s01",
        "May the sacrifice we are about to offer unto Your holy Name, O Lord, make us pure, "
        "and day by day help us to live a more heavenly life. Through our Lord Jesus Christ, "
        "Thy Son, who liveth and reigneth with Thee in the unity of the Holy Ghost, God,",
    ),
    ("proprium.dominica-ii-post-pentecosten-secreta", "s02", "world without end."),
    (
        "proprium.sacratissimi-cordis-iesu-collecta",
        "s01",
        "O God, who mercifully deignest to bestow upon us the infinite treasures of love in "
        "the Heart of Thy Son, wounded by our sins: grant, we beseech Thee, that, offering "
        "Him the devout homage of our piety, we may also fulfill the duty of worthy "
        "reparation. Through the same Lord Jesus Christ, Thy Son, who liveth and reigneth "
        "with Thee in the unity of the Holy Ghost, God, world without end.",
    ),
    (
        "proprium.sacratissimi-cordis-iesu-secreta",
        "s01",
        "Look, we beseech Thee, O Lord, upon the ineffable charity of the Heart of Thy "
        "beloved Son, that what we offer may be an acceptable gift to Thee and an expiation "
        "for our sins. Through the same our Lord Jesus Christ, Thy Son, who liveth and "
        "reigneth with Thee in the unity of the Holy Ghost, God,",
    ),
    ("proprium.sacratissimi-cordis-iesu-secreta", "s02", "world without end."),
    (
        "proprium.sacratissimi-cordis-iesu-postcommunio",
        "s01",
        "May Thy holy gifts, O Lord Jesus, bestow divine fervor upon us, so that, having "
        "tasted the sweetness of Thy most sweet Heart, we may learn to despise earthly "
        "things and love heavenly things, who livest and reignest with God the Father in the "
        "unity of the Holy Ghost, God, world without end.",
    ),
    (
        "proprium.sancti-bartholomaei-apostoli-collecta",
        "s01",
        "Almighty, eternal God, Who bestowed on us the devout and holy joy of this day to "
        "celebrate the feast of Your blessed Apostle Bartholomew, grant unto Your Church, we "
        "beseech You, both to love what he believed and to preach what he taught. Through "
        "our Lord Jesus Christ, Thy Son, who liveth and reigneth with Thee in the unity of "
        "the Holy Ghost, God, world without end.",
    ),
    (
        "proprium.sancti-matthiae-apostoli-collecta",
        "s01",
        "O God, who didst join blessed Matthias to the company of Thy Apostles, grant, we "
        "beseech Thee, that through his intercession we may always feel the tenderness of "
        "Thy mercy toward us. Through our Lord Jesus Christ, Thy Son, who liveth and "
        "reigneth with Thee in the unity of the Holy Ghost, God, world without end.",
    ),
]

CAPTION_PREDECESSORS: list[tuple[str, str, str]] = [
    ("proprium.assumptio-beatae-mariae-virginis-secreta", "w001", "may rise"),
    ("proprium.assumptio-beatae-mariae-virginis-secreta", "w025", "through"),
    ("proprium.corporis-christi-secreta", "w001", "to Your Church"),
    ("proprium.corporis-christi-postcommunio", "w001", "grant"),
    ("proprium.dominica-ii-post-pentecosten-secreta", "w001", "sacrifice"),
    ("proprium.dominica-ii-post-pentecosten-secreta", "w006", "about to be offered"),
    ("proprium.dominica-ii-post-pentecosten-secreta", "w018", "through"),
    ("proprium.sacratissimi-cordis-iesu-postcommunio", "w001", "may bestow"),
    ("proprium.sancti-matthiae-apostoli-collecta", "w021", "through"),
]

ABOUT_PREDECESSORS: list[tuple[str, str]] = [
    (
        "proprium.corporis-christi-collecta",
        "The Collect of the feast of the Most Holy Body of Christ. It asks for such "
        "veneration of the mysteries of the Lord’s Body and Blood that their reception may "
        "continually yield the fruit of redemption.",
    ),
    (
        "proprium.corporis-christi-postcommunio",
        "The Postcommunion of the feast of the Most Holy Body of Christ. It asks to be "
        "filled eternally with the Godhead, foreshadowed by the temporal reception of "
        "Christ’s precious Body and Blood.",
    ),
]


def _inputs(text_id):
    address = text_id.replace(".", "/", 1) + ".json"
    core = json.loads((ROOT / "texts" / address).read_text(encoding="utf-8"))
    layer = json.loads((ROOT / "languages/en/texts" / address).read_text(encoding="utf-8"))
    return core, layer


def _caption(layer, word_id):
    groups = [
        group
        for group in layer["segments"]["s01"].get("alignments", [])
        if word_id in group["words"]
    ]
    assert len(groups) <= 1
    return groups[0]["gloss"] if groups else layer["words"][word_id]["gloss"]


def _set_caption(layer, word_id, value):
    for group in layer["segments"]["s01"].get("alignments", []):
        if word_id in group["words"]:
            group["gloss"] = value
            return
    layer["words"][word_id]["gloss"] = value


def _assert_complete(core, layer, text_id):
    assert core["id"] == layer["text"] == text_id
    words = [word for segment in core["segments"] for word in segment["words"]]
    assert len(words) == WORD_COUNTS[text_id]
    assert [word["id"] for word in words] == list(layer["words"])
    assert {key: row["translation"] for key, row in layer["segments"].items()} == (
        TRANSLATIONS[text_id]
    ), "complete English prose"
    if text_id in ABOUTS:
        assert layer["about"] == ABOUTS[text_id], "oration description"
    for word_id, caption in CAPTIONS.get(text_id, {}).items():
        assert _caption(layer, word_id) == caption, "contextual caption"
    if text_id == "proprium.assumptio-beatae-mariae-virginis-secreta":
        members = ["w005", "w006"]
        touching = [
            group
            for group in layer["segments"]["s01"]["alignments"]
            if set(group["words"]) & set(members)
        ]
        assert touching == [{"words": members, "anchor": "w006", "gloss": "of our devotion"}], (
            "devotion genitive group"
        )
        forms = {word["id"]: word["form"] for word in words}
        assert [forms[word] for word in ["w005", "w006", "w007"]] == [
            "nostræ",
            "devotiónis",
            "oblátio",
        ]
        assert all("gloss" not in layer["words"][word] for word in members)
        assert layer["words"]["w007"]["gloss"] == "the offering"
    if text_id.endswith("-secreta"):
        assert [segment["id"] for segment in core["segments"]] == ["s01", "s02", "s03"]
        assert [segment["speaker"] for segment in core["segments"]] == [
            "sacerdos",
            "sacerdos",
            "minister",
        ]
        assert [segment["voice"] for segment in core["segments"]] == ["secreto", "clara", "clara"]
        assert layer["segments"]["s01"]["translation"].endswith("God,")
        assert layer["segments"]["s02"]["translation"] == "forever and ever."
        assert layer["segments"]["s03"]["translation"] == "Amen."
    else:
        assert [segment["id"] for segment in core["segments"]] == ["s01", "s02"]
        assert layer["segments"]["s02"]["translation"] == "Amen."
    ledger = json.loads(
        (ROOT / "languages/en/translation-provenance.json").read_text(encoding="utf-8")
    )
    sites = {row["site"]: row for row in ledger["sites"]}
    for segment, value in TRANSLATIONS[text_id].items():
        encoded = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        assert sites[f"{text_id}.{segment}.en"]["target_sha256"] == (
            hashlib.sha256(encoded).hexdigest()
        ), "current translation digest"
    assert interlinear.check(core, layer) == []


@contextmanager
def _changed_layer(core, original, text_id):
    _assert_complete(core, original, text_id)
    saved = deepcopy(original)
    changed = deepcopy(original)
    try:
        yield changed
        changed_json = json.dumps(changed, ensure_ascii=False, sort_keys=True)
        saved_json = json.dumps(saved, ensure_ascii=False, sort_keys=True)
        assert changed_json != saved_json, "mutation must change the layer"
    finally:
        changed.clear()
        changed.update(deepcopy(saved))
        assert original == saved
        assert changed == saved
        _assert_complete(core, changed, text_id)


@pytest.mark.parametrize("text_id", list(TRANSLATIONS))
def test_complete_contemporary_orations(text_id):
    _assert_complete(*_inputs(text_id), text_id)


@pytest.mark.parametrize(
    "case",
    PROSE_PREDECESSORS,
    ids=[f"{text}-{segment}" for text, segment, _ in PROSE_PREDECESSORS],
)
def test_actual_prose_predecessor_rejects_and_recovers(case):
    text_id, segment, before = case
    core, original = _inputs(text_id)
    with _changed_layer(core, original, text_id) as changed:
        changed["segments"][segment]["translation"] = before
        with pytest.raises(AssertionError, match="complete English prose"):
            _assert_complete(core, changed, text_id)


@pytest.mark.parametrize(
    "case",
    CAPTION_PREDECESSORS,
    ids=[f"{text}-{word}" for text, word, _ in CAPTION_PREDECESSORS],
)
def test_caption_predecessor_rejects_and_recovers(case):
    text_id, word, before = case
    core, original = _inputs(text_id)
    with _changed_layer(core, original, text_id) as changed:
        _set_caption(changed, word, before)
        with pytest.raises(AssertionError, match="contextual caption"):
            _assert_complete(core, changed, text_id)


@pytest.mark.parametrize(
    "case",
    ABOUT_PREDECESSORS,
    ids=[text for text, _ in ABOUT_PREDECESSORS],
)
def test_description_predecessor_rejects_and_recovers(case):
    text_id, before = case
    core, original = _inputs(text_id)
    with _changed_layer(core, original, text_id) as changed:
        changed["about"] = before
        with pytest.raises(AssertionError, match="oration description"):
            _assert_complete(core, changed, text_id)


def test_original_devotion_partition_rejects_and_recovers():
    text_id = "proprium.assumptio-beatae-mariae-virginis-secreta"
    core, original = _inputs(text_id)
    with _changed_layer(core, original, text_id) as changed:
        changed["segments"]["s01"]["alignments"] = [
            group
            for group in changed["segments"]["s01"]["alignments"]
            if group["words"] != ["w005", "w006"]
        ]
        changed["words"]["w005"]["gloss"] = "of our"
        changed["words"]["w006"]["gloss"] = "devotion"
        with pytest.raises(AssertionError, match="devotion genitive group"):
            _assert_complete(core, changed, text_id)
