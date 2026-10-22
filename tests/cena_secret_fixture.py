"""Local Holy Thursday Secret regressions, not a general translation validator."""

SECRET = "proprium.feria-v-in-cena-domini-secreta"
GROUPS = (
    (5, 6, 6, "holy Father", "vocative"),
    (7, 9, 9, "almighty eternal God", "divine titles"),
    (10, 11, 10, "our sacrifice", "offering object"),
    (12, 13, 12, "may make acceptable", "third-person petition"),
    (15, 16, 15, "to His disciples", "disciples"),
    (17, 19, 19, "in remembrance of Himself", "reflexive purpose"),
    (20, 21, 21, "this to be done", "hoc fieri"),
    (22, 23, 23, "by today’s institution", "institution"),
)
DIRECT = {
    "w001": ("He Himself", "emphatic Christ subject"),
    "w002": ("to You", "Father addressee"),
    "w003": ("we ask", "parenthetic petitioners"),
    "w004": ("Lord", "bare vocative"),
    "w024": ("showed", "completed showing"),
    "w014": ("He who", "relative Christ subject"),
    "w025": ("Jesus", "delayed named subject"),
    "w026": ("Christ", "delayed named subject"),
}
DETAILS = {
    "w001": (
        "The Father is addressed as Lord, holy Father and almighty eternal God. "
        "“He Himself” is Christ, whose name comes later: Jesus Christ, Your Son, our Lord. "
        "The petition asks that Christ make our sacrifice acceptable to the Father. "
        "“We ask” is a parenthetic petition."
    ),
    "w024": (
        "Christ showed His disciples that this was to be done in remembrance of Himself. "
        "“This” refers to the sacrificial action. The Latin delays “showed” until after "
        "“by today’s institution.” “His” and “Himself” refer to Christ, not to the Father. "
        "The wording recalls Christ’s institution of the Eucharist, not Judas’s betrayal."
    ),
}
SOURCE = {
    "w001": {"form": "Ipse", "case": "nom", "number": "sg", "gender": "m"},
    "w002": {"form": "tibi", "case": "dat"},
    "w010": {"form": "sacrifícium", "case": "acc", "number": "sg", "gender": "n"},
    "w012": {
        "form": "reddat",
        "person": 3,
        "number": "sg",
        "tense": "pres",
        "mood": "subj",
        "voice": "act",
    },
    "w013": {"form": "accéptum", "case": "acc", "gender": "n", "head": "w010"},
    "w014": {"form": "qui", "case": "nom", "gender": "m"},
    "w015": {"form": "discípulis", "case": "dat", "number": "pl"},
    "w016": {"form": "suis", "head": "w015"},
    "w018": {"form": "sui", "lemma": "sui", "case": "gen"},
    "w020": {"form": "hoc", "case": "acc", "gender": "n"},
    # Fio's selected active form carries the passive sense of facio here.
    "w021": {"form": "fíeri", "lemma": "fio", "tense": "pres", "mood": "inf", "voice": "act"},
    "w022": {"form": "hodiérna", "case": "abl", "head": "w023"},
    "w023": {"form": "traditióne", "case": "abl"},
    "w024": {"form": "monstrávit", "tense": "perf", "person": 3, "voice": "act"},
    "w025": {"form": "Iesus", "case": "nom", "gender": "m"},
}


def ids(first, last):
    return [f"w{number:03}" for number in range(first, last + 1)]


def assert_secret_source(core):
    words = {w["id"]: w for s in core["segments"] for w in s.get("words", [])}
    assert core["id"] == SECRET and set(SOURCE) <= words.keys(), "Secret selected source roles"
    for wid, expected in SOURCE.items():
        word = words[wid]
        actual = {
            key: word.get(key) if key in {"form", "lemma", "head"} else word["morph"].get(key)
            for key in expected
        }
        assert actual == expected, "Secret selected source roles: " + wid


def assert_secret_scope(layer):
    assert layer["text"] == SECRET and layer["language"] == "en", "Secret English identity"
    alignments = layer["segments"]["s01"]["alignments"]
    for first, last, anchor, caption, label in GROUPS:
        members = ids(first, last)
        actual = [a for a in alignments if set(a["words"]) & set(members)]
        expected = {"words": members, "anchor": f"w{anchor:03}", "gloss": caption}
        assert actual == [expected], "Secret compact expression: " + label
        assert all(not layer["words"][wid].get("gloss") for wid in members), (
            "Secret single provider: " + label
        )
    for wid, (caption, label) in DIRECT.items():
        assert layer["words"][wid].get("gloss") == caption, "Secret " + label
        assert not any(wid in a["words"] for a in alignments), "Secret direct provider: " + wid
    for wid, explanation in DETAILS.items():
        assert layer["words"][wid].get("explanation") == explanation, "Secret useful detail: " + wid
    for first, last, anchor, caption in ((27, 28, 27, "Your Son"), (29, 30, 29, "our Lord")):
        members = ids(first, last)
        assert [a for a in alignments if set(a["words"]) & set(members)] == [
            {"words": members, "anchor": f"w{anchor:03}", "gloss": caption}
        ], "Secret delayed Son identity"
