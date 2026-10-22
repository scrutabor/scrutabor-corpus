"""Polish captions for mid-sentence relatives, ablative absolutes and split phrases."""

import json
import re
from copy import deepcopy
from pathlib import Path

import pytest

from checks import interlinear, language_packs, prose
from checks.translation_provenance import canonical_hash, source_payload

ROOT = Path(__file__).resolve().parents[1]
P = "proprium."
SEVEN = P + "septem-dolorum-beatae-mariae-virginis-secreta"
OFFERTORY = P + "commemoratio-omnium-fidelium-defunctorum-missa-i-offertorium"
QUEENSHIP_HEART = P + "immaculatum-cor-beatae-mariae-virginis-postcommunio"

# case, text, segment, words, Latin forms, anchor, gloss, historical direct glosses
GROUPS = (
    (
        "lateran-secret-te-adiuvante",
        P + "dedicatio-archibasilicae-sanctissimi-salvatoris-secreta",
        "s01",
        ("w015", "w016"),
        ("te", "adiuvánte"),
        "w016",
        "przy Twoim wsparciu",
        ("Tobą", "wspierającym"),
    ),
    (
        "advent-i-collect-te-liberante",
        P + "dominica-i-adventus-collecta",
        "s01",
        ("w018", "w019"),
        ("te", "liberánte"),
        "w019",
        "dzięki Twemu wyzwoleniu",
        ("przez Ciebie", "wyzwalającego"),
    ),
    (
        "exaltation-postcommunion-eius-subsidiis",
        P + "exaltatio-sanctae-crucis-postcommunio",
        "s01",
        ("w013", "w014", "w015", "w016", "w017"),
        ("eius", "quoque", "perpétuis", "defénde", "subsídiis"),
        "w016",
        "broń także jego nieustanną pomocą",
        ("jego", "także", "nieustanną", "broń", "pomocą"),
    ),
    (
        "pentecost-xxii-secret-ab-adversis",
        P + "dominica-xxii-post-pentecosten-secreta",
        "s01",
        ("w016", "w017", "w018", "w019"),
        ("ab", "ómnibus", "tueátur", "advérsis"),
        "w018",
        "broniła przed wszystkimi przeciwnościami",
        ("od", "wszystkich", "broniła", "przeciwności"),
    ),
    (
        "pentecost-v-postcommunion-ab-insidiis",
        P + "dominica-v-post-pentecosten-postcommunio",
        "s01",
        ("w014", "w015", "w016", "w017"),
        ("ab", "hóstium", "liberémur", "insídiis"),
        "w016",
        "zostali wyzwoleni od zasadzek nieprzyjaciół",
        ("od", "nieprzyjaciół", "zostali wyzwoleni", "zasadzek"),
    ),
)

# The Seven Sorrows intercession: possessor, companions and means, captioned separately.
SEVEN_SPAN = ("w022", "w023", "w024", "w025", "w026", "w027", "w028", "w029", "w030")
SEVEN_FORMS = (
    "suo",
    "suorúmque",
    "sub",
    "Cruce",
    "Sanctórum",
    "consórtium",
    "multiplicáto",
    "piíssimo",
    "intervéntu",
)
SEVEN_DIRECT = {"w022": "jej"}
SEVEN_GROUPS = (
    {
        "words": ["w023", "w024", "w025", "w026", "w027"],
        "anchor": "w027",
        "gloss": "i jej świętych towarzyszy pod Krzyżem",
    },
    {
        "words": ["w028", "w029", "w030"],
        "anchor": "w030",
        "gloss": "dzięki wzmożonemu, najłaskawszemu wstawiennictwu",
    },
)
SEVEN_HISTORICAL = {
    "words": ["w022", "w023", "w024", "w025", "w026", "w027", "w028", "w029", "w030"],
    "anchor": "w030",
    "gloss": "dzięki wzmożonemu, najłaskawszemu wstawiennictwu jej i jej świętych towarzyszy "
    "pod Krzyżem",
}

# case, text, segment, word, Latin form, gloss, historical gloss, continuing prose
RELATIVES = (
    (
        "epiphany-gospel-qui-natus",
        P + "epiphania-domini-evangelium",
        "s01",
        "w021",
        "qui",
        "Ten, który",
        "Ten Który",
        "Gdzie jest Ten, który narodził się",
    ),
    (
        "epiphany-secret-quod-declaratur",
        P + "epiphania-domini-secreta",
        "s01",
        "w017",
        "quod",
        "Ten, który",
        "Ten Który",
        "lecz Ten, którego owe dary oznaczają",
    ),
    (
        "immaculate-conception-communion-qui-potens",
        P + "immaculata-conceptio-communio",
        "s01",
        "w011",
        "qui",
        "Ten, który",
        "Ten, Który",
        "Ten, który jest potężny",
    ),
    (
        "christmas-dawn-epistle-quem-effudit",
        P + "nativitas-domini-in-aurora-epistola",
        "s01",
        "w030",
        "quem",
        "którego",
        "Którego",
        "Ducha Świętego, którego obficie wylał",
    ),
    (
        "christmas-dawn-introit-cuius-regni",
        P + "nativitas-domini-in-aurora-introitus",
        "s01",
        "w020",
        "cuius",
        "którego",
        "Którego",
        "przyszłego wieku, którego królestwu",
    ),
    (
        "christmas-dawn-introit-reprise-cuius-regni",
        P + "nativitas-domini-in-aurora-introitus",
        "s01",
        "w076",
        "cuius",
        "którego",
        "Którego",
        "przyszłego wieku, którego królestwu",
    ),
    (
        "christmas-dawn-postcommunion-cuius-nativitas",
        P + "nativitas-domini-in-aurora-postcommunio",
        "s01",
        "w009",
        "cuius",
        "którego",
        "Którego",
        "tego sakramentu, którego jedyne",
    ),
    (
        "purification-gospel-quod-parasti",
        P + "purificatio-beatae-mariae-virginis-evangelium",
        "s01",
        "w139",
        "Quod",
        "które",
        "Które",
        "Twoje zbawienie, które przygotowałeś",
    ),
    (
        "purification-tract-quod-parasti",
        P + "purificatio-beatae-mariae-virginis-tractus",
        "s01",
        "w049",
        "Quod",
        "które",
        "Które",
        "Twoje zbawienie, które przygotowałeś",
    ),
)

# case, text, word, Latin forms the note quotes, note
EXPLANATIONS = (
    (
        "michael-secret-angelico-suffragio",
        P + "dedicatio-sancti-michaelis-archangeli-secreta",
        "w013",
        ("angélico", "interveniénte", "suffrágio", "pro", "nobis"),
        "Słowa „angélico … interveniénte suffrágio” to ablativus absolutus. Polszczyzna oddaje go "
        "wyrażeniem przyimkowym: „za anielskim orędownictwem, wstawiającym się za nami”. Słowa "
        "„pro nobis” (za nami) stoją wewnątrz tej konstrukcji. Określa ona obie prośby: „przyjął” "
        "i „sprawił”.",
    ),
    (
        "seven-sorrows-secret-suo-interventu",
        SEVEN,
        "w022",
        ("suo", "intervéntu", "suorúmque", "Sanctórum", "consórtium"),
        "Słowo „suo” (jej) należy do „intervéntu” na końcu wyrażenia. Wskazuje Maryję, a nie "
        "podmiot zdania („my”), dlatego po polsku „jej”, a nie „swój”. Do tego samego "
        "wstawiennictwa odnoszą się słowa „suorúmque … Sanctórum consórtium” (i jej świętych "
        "towarzyszy). Całość to ablativus absolutus: „dzięki wzmożonemu, najłaskawszemu "
        "wstawiennictwu jej i jej świętych towarzyszy pod Krzyżem”.",
    ),
)

OFFERTORY_LOWER = "w światłości świętej: którą niegdyś obiecałeś"
OFFERTORY_CAPITAL = "w światłości świętej: Którą niegdyś obiecałeś"
OFFERTORY_REPETENDUM = "do życia. Które niegdyś obiecałeś"
OFFERTORY_ROW = {"origin": "working-unsettled", "review": "working", "familiar_core": False}

CAPITAL_RELATIVE = re.compile(
    r"(?<![\w])Któr(?:y|a|e|ego|ej|emu|ym|ymi|ych|zy|ą)(?:ż|ś|kolwiek)?\b"
)
# Two Exaltation relatives are adjudicated together with those prayers' verb government;
# either case passes this corpus-wide guard.
SEPARATELY_PINNED = {
    (P + "exaltatio-sanctae-crucis-collecta", "w015"),
    (P + "exaltatio-sanctae-crucis-secreta", "w010"),
}
# The epistle quotes Ps 103:4 after "mówi:", and its quotations begin with a capital.
QUOTATION_AFTER_COLON = {(P + "nativitas-domini-in-die-epistola", "s01")}


def require(condition, message):
    if not condition:
        raise AssertionError(message)


def document(text, language=None):
    prefix = ROOT if language is None else ROOT / "languages" / language
    path = prefix / "texts" / (text.replace(".", "/", 1) + ".json")
    return json.loads(path.read_text(encoding="utf-8"))


TEXTS = sorted(
    {row[1] for row in (*GROUPS, *RELATIVES, *EXPLANATIONS)} | {SEVEN, OFFERTORY, QUEENSHIP_HEART}
)


@pytest.fixture(scope="module")
def documents():
    return {text: {None: document(text), "pl": document(text, "pl")} for text in TEXTS}


def segment_of(core, segment_id):
    (segment,) = [segment for segment in core["segments"] if segment["id"] == segment_id]
    return segment


def touching(layer, segment_id, words):
    return [
        group
        for group in layer["segments"][segment_id].get("alignments", [])
        if set(group["words"]) & set(words)
    ]


def assert_group(core, layer, row):
    _, _, segment_id, words, forms, anchor, gloss, _ = row
    order = segment_of(core, segment_id)["words"]
    ids = [word["id"] for word in order]
    start = ids.index(words[0])
    require(tuple(ids[start : start + len(words)]) == words, "compact caption group")
    require(
        tuple(word["form"].rstrip(",.:;") for word in order[start : start + len(words)]) == forms,
        "Latin construction identity",
    )
    expected = {"words": list(words), "anchor": anchor, "gloss": gloss}
    require(touching(layer, segment_id, words) == [expected], "compact caption group")
    require(len(words) <= 5, "compact caption group")
    require(all("gloss" not in layer["words"][word] for word in words), "once-only caption")
    require(interlinear.check(core, layer) == [], "once-only caption")


@pytest.mark.parametrize("row", GROUPS, ids=[row[0] for row in GROUPS])
def test_construction_is_one_compact_caption(documents, row):
    texts = documents[row[1]]
    assert_group(texts[None], texts["pl"], row)


def assert_seven(core, layer):
    order = segment_of(core, "s01")["words"]
    ids = [word["id"] for word in order]
    start = ids.index(SEVEN_SPAN[0])
    require(
        tuple(word["form"] for word in order[start : start + len(SEVEN_SPAN)]) == SEVEN_FORMS,
        "Latin construction identity",
    )
    require(touching(layer, "s01", SEVEN_SPAN) == list(SEVEN_GROUPS), "compact caption group")
    direct = {wid: layer["words"][wid].get("gloss") for wid in SEVEN_SPAN}
    require(
        {wid: gloss for wid, gloss in direct.items() if gloss} == SEVEN_DIRECT,
        "compact caption group",
    )
    require(max(len(group["words"]) for group in SEVEN_GROUPS) <= 5, "compact caption group")
    require(interlinear.check(core, layer) == [], "once-only caption")


def test_seven_sorrows_intercession_is_decomposed(documents):
    texts = documents[SEVEN]
    assert_seven(texts[None], texts["pl"])
    words = {word["id"]: word for word in segment_of(texts[None], "s01")["words"]}
    assert words["w022"]["head"] == "w030" and words["w023"]["head"] == "w027"
    assert SEVEN_HISTORICAL["gloss"] in texts["pl"]["segments"]["s01"]["translation"]


def assert_relative(core, layer, row):
    _, _, segment_id, word, form, gloss, _, continuing = row
    order = segment_of(core, segment_id)["words"]
    (index,) = [i for i, item in enumerate(order) if item["id"] == word]
    require(index > 0 and order[index]["form"] == form, "Latin relative identity")
    require(order[index]["lemma"] == "qui", "Latin relative identity")
    require(touching(layer, segment_id, [word]) == [], "Polish relative caption case")
    require(layer["words"][word].get("gloss") == gloss, "Polish relative caption case")
    require(not CAPITAL_RELATIVE.search(gloss), "Polish relative caption case")
    require(continuing in layer["segments"][segment_id]["translation"], "continuing prose")


@pytest.mark.parametrize("row", RELATIVES, ids=[row[0] for row in RELATIVES])
def test_mid_sentence_relative_is_lowercase(documents, row):
    texts = documents[row[1]]
    assert_relative(texts[None], texts["pl"], row)


def assert_explanation(core, layer, english, row):
    _, _, word, forms, note = row
    requirement = (core["localization"].get("explanations") or {}).get(word)
    require(requirement == {"languages": ["pl"]}, "construction explanation scope")
    require(layer["words"][word].get("explanation") == note, "construction explanation")
    require("explanation" not in english["words"][word], "construction explanation scope")
    latin = {item["form"].rstrip(",.:;") for s in core["segments"] for item in s["words"]}
    require(set(forms) <= latin, "construction explanation")
    require(
        all(re.search(rf"(?<!\w){re.escape(form)}(?!\w)", note) for form in forms),
        "construction explanation",
    )


@pytest.mark.parametrize("row", EXPLANATIONS, ids=[row[0] for row in EXPLANATIONS])
def test_hidden_relation_has_a_polish_explanation(documents, row):
    core, layer = documents[row[1]][None], documents[row[1]]["pl"]
    english = document(row[1], "en")
    assert_explanation(core, layer, english, row)
    assert language_packs.check_core(core) == []
    for language, data in (("pl", layer), ("en", english)):
        path = ROOT / "languages" / language / "texts" / (row[1].replace(".", "/", 1) + ".json")
        assert language_packs.check_layer(core, data, path) == []
    assert prose.check(layer) == []


def ledger_row():
    rows = json.loads(
        (ROOT / "languages/pl/translation-provenance.json").read_text(encoding="utf-8")
    )["sites"]
    (row,) = [row for row in rows if row["site"] == f"{OFFERTORY}.s01.pl"]
    return row


def assert_offertory(core, layer, row):
    translation = layer["segments"]["s01"]["translation"]
    require(translation.count(OFFERTORY_LOWER) == 1, "Polish prose relative case")
    require(OFFERTORY_CAPITAL not in translation, "Polish prose relative case")
    require(translation.count(OFFERTORY_REPETENDUM) == 1, "Polish prose repetendum")
    require(row["target_sha256"] == canonical_hash(translation), "ledger target identity")
    require(
        row["source_sha256"] == canonical_hash(source_payload(segment_of(core, "s01"))),
        "ledger source identity",
    )
    require({key: row[key] for key in OFFERTORY_ROW} == OFFERTORY_ROW, "ledger status")


def test_offertory_relative_after_a_colon_is_lowercase(documents):
    texts = documents[OFFERTORY]
    assert_offertory(texts[None], texts["pl"], ledger_row())


def assert_sentence_initial(core, layer):
    first = segment_of(core, "s01")["words"][0]
    require(first["id"] == "w001" and first["form"] == "Divínis", "Latin sentence start")
    require(touching(layer, "s01", ["w001"]) == [], "sentence-initial caption capital")
    require(layer["words"]["w001"].get("gloss") == "Boskimi", "sentence-initial caption capital")
    require(
        layer["segments"]["s01"]["translation"].startswith("Posileni boskimi darami"),
        "sentence-initial caption capital",
    )


def test_sentence_initial_quality_adjective_keeps_its_capital(documents):
    texts = documents[QUEENSHIP_HEART]
    assert_sentence_initial(texts[None], texts["pl"])


def capital_relative_sites(root):
    """Capitalized Polish relatives in captions whose Latin word follows unpunctuated text."""
    captions, prose_sites = set(), set()
    for path in sorted((root / "languages/pl/texts").rglob("*.json")):
        layer = json.loads(path.read_text(encoding="utf-8"))
        core = document(layer["text"])
        for segment in core["segments"]:
            words = segment.get("words") or []
            local = layer["segments"].get(segment["id"]) or {}
            groups = {g["words"][0]: g for g in local.get("alignments", []) if "gloss" in g}
            for index, word in enumerate(words[1:], 1):
                gloss = (groups.get(word["id"]) or {}).get("gloss") or layer["words"][
                    word["id"]
                ].get("gloss")
                previous = words[index - 1].get("post", "")
                if gloss and previous in {"", ","} and CAPITAL_RELATIVE.search(gloss):
                    captions.add((layer["text"], word["id"]))
            translation = local.get("translation") or ""
            if re.search(r"[,:]\s+" + CAPITAL_RELATIVE.pattern, translation):
                prose_sites.add((layer["text"], segment["id"]))
    return captions, prose_sites


def test_no_unreviewed_mid_sentence_capital_relative():
    captions, prose_sites = capital_relative_sites(ROOT)
    assert captions <= SEPARATELY_PINNED
    assert prose_sites == QUOTATION_AFTER_COLON


def restore_group(layer, row):
    _, _, segment_id, words, _, _, _, historical = row
    groups = layer["segments"][segment_id]["alignments"]
    groups[:] = [g for g in groups if g["words"] != list(words)]
    for word, gloss in zip(words, historical, strict=True):
        layer["words"][word]["gloss"] = gloss


GROUP_MUTANTS = [row[0] for row in GROUPS]


@pytest.mark.parametrize("case", GROUP_MUTANTS)
def test_group_guard_rejects_the_split_caption_and_restores(documents, case):
    (row,) = [row for row in GROUPS if row[0] == case]
    core, layer = documents[row[1]][None], documents[row[1]]["pl"]
    snapshot = deepcopy(layer)
    broken = deepcopy(layer)
    restore_group(broken, row)
    assert broken != layer
    with pytest.raises(AssertionError) as caught:
        assert_group(core, broken, row)
    assert str(caught.value) == "compact caption group"
    assert_group(core, layer, row)
    assert layer == snapshot


def test_seven_sorrows_guard_rejects_the_nine_word_group_and_restores(documents):
    core, layer = documents[SEVEN][None], documents[SEVEN]["pl"]
    snapshot = deepcopy(layer)
    broken = deepcopy(layer)
    broken["segments"]["s01"]["alignments"] = [deepcopy(SEVEN_HISTORICAL)]
    for word in SEVEN_SPAN:
        broken["words"][word].pop("gloss", None)
    assert interlinear.check(core, broken) == []
    with pytest.raises(AssertionError) as caught:
        assert_seven(core, broken)
    assert str(caught.value) == "compact caption group"
    assert_seven(core, layer)
    assert layer == snapshot


@pytest.mark.parametrize("row", RELATIVES, ids=[row[0] for row in RELATIVES])
def test_relative_guard_rejects_the_capital_and_restores(documents, row):
    core, layer = documents[row[1]][None], documents[row[1]]["pl"]
    snapshot = deepcopy(layer)
    broken = deepcopy(layer)
    broken["words"][row[3]]["gloss"] = row[6]
    with pytest.raises(AssertionError) as caught:
        assert_relative(core, broken, row)
    assert str(caught.value) == "Polish relative caption case"
    assert_relative(core, layer, row)
    assert layer == snapshot


@pytest.mark.parametrize("defect", ["omitted", "widened"])
def test_explanation_guard_rejects_a_lost_or_widened_note(documents, defect):
    row = EXPLANATIONS[1]
    core, layer = documents[row[1]][None], documents[row[1]]["pl"]
    english = document(row[1], "en")
    snapshot = deepcopy(documents[row[1]])
    broken_core, broken_layer = deepcopy(core), deepcopy(layer)
    if defect == "omitted":
        del broken_layer["words"][row[2]]["explanation"]
        expected, checked, language = "construction explanation", broken_layer, "pl"
    else:
        broken_core["localization"]["explanations"][row[2]] = {}
        expected, checked, language = "construction explanation scope", english, "en"
    with pytest.raises(AssertionError) as caught:
        assert_explanation(broken_core, broken_layer, english, row)
    assert str(caught.value) == expected
    path = ROOT / "languages" / language / "texts" / (row[1].replace(".", "/", 1) + ".json")
    assert any(
        "explanation topology differs" in error
        for error in language_packs.check_layer(broken_core, checked, path)
    )
    assert_explanation(core, layer, english, row)
    assert documents[row[1]] == snapshot


@pytest.mark.parametrize("defect", ["capital", "stale-ledger"])
def test_offertory_guard_rejects_a_capital_or_stale_ledger(documents, defect):
    core, layer = documents[OFFERTORY][None], documents[OFFERTORY]["pl"]
    row = ledger_row()
    broken = deepcopy(layer)
    segment = broken["segments"]["s01"]
    if defect == "capital":
        segment["translation"] = segment["translation"].replace(
            OFFERTORY_LOWER, OFFERTORY_CAPITAL, 1
        )
        broken_row = dict(row, target_sha256=canonical_hash(segment["translation"]))
        expected = "Polish prose relative case"
    else:
        segment["translation"] = segment["translation"].replace("Michał", "Michael", 1)
        broken_row = dict(row)
        expected = "ledger target identity"
    assert broken != layer
    with pytest.raises(AssertionError) as caught:
        assert_offertory(core, broken, broken_row)
    assert str(caught.value) == expected
    assert_offertory(core, layer, row)


def test_sentence_initial_guard_rejects_a_lowercase_start(documents):
    core, layer = documents[QUEENSHIP_HEART][None], documents[QUEENSHIP_HEART]["pl"]
    broken = deepcopy(layer)
    broken["words"]["w001"]["gloss"] = "boskimi"
    with pytest.raises(AssertionError) as caught:
        assert_sentence_initial(core, broken)
    assert str(caught.value) == "sentence-initial caption capital"
    assert_sentence_initial(core, layer)


def test_corpus_guard_sees_a_restored_mid_sentence_capital(tmp_path):
    row = RELATIVES[3]
    relative = Path("languages/pl/texts") / (row[1].replace(".", "/", 1) + ".json")
    copy = tmp_path / "languages/pl/texts"
    for path in (ROOT / "languages/pl/texts").rglob("*.json"):
        target = copy / path.relative_to(ROOT / "languages/pl/texts")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(path.read_bytes())
    layer = json.loads((tmp_path / relative).read_text(encoding="utf-8"))
    layer["words"][row[3]]["gloss"] = row[6]
    (tmp_path / relative).write_text(json.dumps(layer, ensure_ascii=False), encoding="utf-8")
    captions, prose_sites = capital_relative_sites(tmp_path)
    assert (row[1], row[3]) in captions
    assert prose_sites == QUOTATION_AFTER_COLON
    assert capital_relative_sites(ROOT)[0] <= SEPARATELY_PINNED
