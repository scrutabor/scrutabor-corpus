"""Four source claims keep what the Missal prints apart from what its rubrics supply.

The Confiteor's ministerial form applies the two substitutions its rubric prints.
Ecce Agnus Dei and Panem caelestem print Domine, non sum dignus once and repeat it
by rubric, ending in animam tuam and animam meam respectively. The Trinity
Introit's proper page prints twenty-five words and two cues; the selected reading
expands the common doxology and the antiphon reprise. Its Missal witness declares
that expansion and names the p. 219 locus that prints the doxology consecutively,
while the historical p. 401 locator stays where it was.
"""

import json
import unicodedata
from copy import deepcopy
from pathlib import Path

import pytest
from main_ordo_consumer_fixture import before_main_ordo_records

from build_reader import bibliography
from build_reader.bibliography_bindings import (
    BindingError,
    digest,
    selected_text,
    source_dependencies,
    text_document,
    transcript_digest,
    witness_subject,
)

ROOT = Path(__file__).resolve().parents[1]
EDITION = "edition.missale-romanum.1962-typica"
ITEM = "item.missale-romanum.1962-typica.ia"
CONFITEOR = "ordinarium.confiteor"
ECCE = "ordinarium.ecce-agnus-dei"
PANEM = "ordinarium.panem-caelestem"
TRINITY = "proprium.sanctissimae-trinitatis-introitus"
SUPPLEMENT = f"use.{TRINITY}.expanded-doxology.mr1962"
GENERIC = "complete 1962 liturgical component"

CLAIMS = {
    CONFITEOR: (
        "The Ordo Missae prints the celebrant’s Confiteor across pp. 219–220. The rubric "
        "on p. 220 directs the ministers to repeat it with tibi, pater and te, pater in "
        "place of vobis, fratres and vos, fratres. The selected ministerial form applies "
        "those substitutions; it is not a second complete printed formula."
    ),
    ECCE: (
        "Ritus servandus X.6 prints Ecce Agnus Dei, one complete Domine, non sum dignus "
        "petition, and the distribution formula ending animam tuam. Its direction Quibus "
        "verbis tertio repetitis supplies the threefold petition in the selected reading; "
        "the seventy-one-word expansion is not printed consecutively."
    ),
    PANEM: (
        "Pages 314–315 print Panem caelestem, one complete Domine, non sum dignus petition "
        "under ter dicit, and the communion formula ending animam meam. The selected "
        "reading expands that petition three times according to the rubric; three complete "
        "copies are not printed there."
    ),
    TRINITY: (
        "Page 366 prints the fourteen-word antiphon and eleven-word psalm verse, followed "
        "by Gloria Patri and Benedicta cues. The selected reading expands the twenty-word "
        "doxology and repeats the antiphon. Page 401 attests the doxology in two halves "
        "separated by an Et laudabili refrain, not as one uninterrupted Introit formula."
    ),
}
# Inclusive word ranges: printed at the cited location, or supplied by its rubric or cue.
SCOPE = {
    CONFITEOR: {
        "printed": ((1, 21), (24, 57), (60, 66)),
        "supplied": ((22, 23), (58, 59)),
    },
    ECCE: {
        "printed": ((1, 25), (60, 71)),
        "supplied": ((26, 59),),
    },
    PANEM: {
        "printed": ((1, 24), (59, 70)),
        "supplied": ((25, 58),),
    },
    TRINITY: {
        "printed": ((1, 25),),
        "supplied": ((26, 45), (46, 59)),
    },
}
COUNTS = {CONFITEOR: (66, 62, 4), ECCE: (71, 37, 34), PANEM: (70, 36, 34), TRINITY: (59, 25, 34)}
# Locator, date, decision and evidence of each primary use stay as they were.
PRIMARY = {
    CONFITEOR: {
        "locator": {
            "printed": "pp. 219–220",
            "scan": "leaves n298–n299 / PDF pp. 299–300",
            "page_url": "https://archive.org/details/missale-romanum-1962/page/n298/mode/1up",
        },
        "verified_on": "2026-09-25",
        "decision": "RETAIN",
        "evidence_sha256": "ee8d1c45f6cc759518ae59a1dd047dfa80033904ba5ce1799fbaa2334df9ee55",
    },
    ECCE: {
        "locator": {
            "printed": "p. lvii",
            "scan": "leaf n62 / PDF p. 63",
            "page_url": "https://archive.org/details/missale-romanum-1962/page/n62/mode/1up",
        },
        "verified_on": "2026-09-25",
        "decision": "RETAIN",
        "evidence_sha256": "3949cb8eadab9642b6f1d99baef1a7bed87bf84b4ab225c79fa83a58a4d215e9",
    },
    PANEM: {
        "locator": {
            "printed": "pp. 314–315",
            "scan": "leaves n395–n396 / PDF pp. 396–397",
            "page_url": "https://archive.org/details/missale-romanum-1962/page/n395/mode/1up",
        },
        "verified_on": "2026-09-25",
        "decision": "RETAIN",
        "evidence_sha256": "54b8eff70c464fed19219b37427a121119c904112e1a72506d92989ecd22cafd",
    },
    TRINITY: {
        "locator": {
            "printed": "p. 366; expanded doxology attested on p. 401",
            "scan": "leaf n447 / PDF p. 448; leaf n482 / PDF p. 483",
            "page_url": "https://archive.org/details/missale-romanum-1962/page/n447/mode/1up",
        },
        "verified_on": "2026-08-31",
        "decision": "RETAIN",
        "evidence_sha256": "1e4659d2b0dc8b7801bd16759fb45ec22c6fa26f7553582cb26943ef9375cf30",
    },
}
# The complete Latin/ritual subject: every word, its punctuation, segments, speakers and voices.
SELECTED = {
    CONFITEOR: "83f73dded14863356ae3a7fbcf2be0da6c5a3d10688a9c045c193467c7df005b",
    ECCE: "3ee355c1e19118c15df1afc8ed03b27dc781e3e3dfd3f69cd3280f2c5c9b84e9",
    PANEM: "425bad6ccca3d47a6577095b2fb35ebd01b6924a3cf1364800012715d1cba8b8",
    TRINITY: "a541c20a82b4388f65d7cd342e83a08396ac220789e803fd95f1ae126fad1715",
}
ASSEMBLY = {
    CONFITEOR: (
        "# assembly: the Missal prints the Confíteor once, for the celebrant (pp. "
        "219-220). The rubric on p. 220 has the ministers repeat it with tibi, pater and "
        "te, pater where he says vobis, fratres and vos, fratres, and this witness applies "
        "those two substitutions and nothing else"
    ),
    ECCE: (
        "# assembly: the Ritus servandus (X, 6) prints Dómine, non sum dignus ... ánima "
        "mea once and directs Quibus verbis tertio repetitis, and this witness repeats it "
        "three times"
    ),
    PANEM: (
        "# assembly: p. 315 prints Dómine, non sum dignus ... ánima mea once, under the "
        "rubric ter dicit, and this witness repeats it three times"
    ),
}
PETITIONS = {ECCE: (9, 25), PANEM: (8, 24)}
NOT_PRINTED = {
    ECCE: "the seventy-one-word expansion is not printed consecutively",
    PANEM: "three complete copies are not printed there",
}
DOXOLOGY = [
    "Glória",
    "Patri",
    "et",
    "Fílio",
    "et",
    "Spirítui",
    "Sancto",
    "Sicut",
    "erat",
    "in",
    "princípio",
    "et",
    "nunc",
    "et",
    "semper",
    "et",
    "in",
    "sǽcula",
    "sæculórum",
    "Amen",
]
DOXOLOGY_LINE = (
    "Glória Patri, et Fílio, et Spirítui Sancto. Sicut erat in princípio, et nunc, et "
    "semper: et in sǽcula sæculórum. Amen."
)
TRINITY_METHOD = (
    "Transcribed from the directly viewed page image of the Benziger Brothers 1962 Editio "
    "iuxta typicam and independently collated against the pinned Divinum Officium witness; "
    "all divergences are declared in the apparatus. Source-scope qualification: p. 366 "
    "prints twenty-five proper words and Gloria Patri / Benedicta cues, not all fifty-nine "
    "selected positions. The twenty-word doxology and fourteen-word antiphon reprise are "
    "expanded. The historical p. 401 wording locus has interposed Et laudabili refrains; "
    "the additional p. 219 locus supplies the twenty doxology words consecutively. This "
    "qualification does not renew the earlier collation or determine ritual roles."
)
TRINITY_PROFILE = "exact-source-with-declared-expansion"
TRINITY_BASIS = (
    "Directly viewed Benziger 1962 proper, with explicit common doxology and "
    "antiphon-reprise expansion; pp. 401 and 219 are additional loci within the same "
    "edition, not independent printed witness families."
)
HISTORICAL_HEADERS = [
    "# witness: mr",
    "# description: Missale Romanum, Benziger Brothers, New York, 1962, editio iuxta typicam",
    "# source: https://archive.org/details/missale-romanum-1962",
    (
        "# location: printed p. 366; expanded doxology attested on p. 401; leaf n447 / PDF "
        "p. 448; leaf n482 / PDF p. 483"
    ),
    "# page-image: https://archive.org/details/missale-romanum-1962/page/n447/mode/1up",
    (
        "# path: p. 366; expanded doxology attested on p. 401 (leaf n447 / PDF p. 448; "
        "leaf n482 / PDF p. 483)"
    ),
    "# historical-transcribed: 2026-08-31 from the 600 dpi page image, not from OCR",
    (
        "# correction: 2026-10-07 the scanned book is the Benziger Brothers editio iuxta "
        "typicam (title page leaf n6, approbation leaf n8), not the typical edition; the "
        "item's scandata.xml and item-meta.xml record its page images at 300 dpi"
    ),
    "# orthography: exact printed accents, ligatures, capitalization, and punctuation",
    (
        "# note: headings, scripture references, typographic crosses, and rubrics outside "
        "the text boundary are edition framing"
    ),
    (
        "# recollated: 2026-09-25, punctuation re-read from the page image at 1 place; the "
        "earlier file had followed the digital source there"
    ),
    (
        "# recollated: 2026-09-25 against the page image: the antiphon opens Benedícta "
        "with its accent, as its repeat does"
    ),
]
QUALIFIER = (
    "# source-scope-qualification: p. 366 prints the antiphon and psalm verse, then Gloria "
    "Patri. and Benedicta. cues; the doxology and antiphon reprise below are expanded. The "
    "historical p. 401 locus prints the doxology in two halves with Et laudabili refrains "
    "between and after them; those refrains are not part of this Introit. The additional "
    "p. 219 locus (leaf n298 / PDF p. 299) prints the twenty doxology words consecutively. "
    "Existing historical location/orthography notes above are retained, not renewed as a "
    "claim of continuous printing on p. 366."
)
SUPPLEMENT_RECORD = {
    "id": "use.proprium.sanctissimae-trinitatis-introitus.expanded-doxology.mr1962",
    "edition": "edition.missale-romanum.1962-typica",
    "digital_item": "item.missale-romanum.1962-typica.ia",
    "role": "official_text",
    "address": {
        "kind": "word",
        "text": "proprium.sanctissimae-trinitatis-introitus",
        "word": "w026",
    },
    "locator": {
        "printed": "p. 219, Ordo Missae, Gloria Patri / Sicut erat",
        "scan": "leaf n298 / PDF p. 299",
        "page_url": "https://archive.org/details/missale-romanum-1962/page/n298/mode/1up",
    },
    "claim": (
        "The page prints the twenty words of Gloria Patri and Sicut erat consecutively, "
        "through Amen, supplying the wording of w026–w045 expanded from the Trinity "
        "proper’s Gloria Patri cue. Its S./M. framing is not evidence for the Trinity "
        "Introit’s performer."
    ),
    "verified_on": "2026-10-18",
    "decision": "RETAIN",
    "evidence_sha256": "ee8d1c45f6cc759518ae59a1dd047dfa80033904ba5ce1799fbaa2334df9ee55",
}
PATH_MARKERS = ("/Users/", "../private", "private/witnesses", ".jp2", "file:")


@pytest.fixture(scope="module")
def data() -> dict:
    return json.loads((ROOT / "bibliography" / "graph.json").read_text(encoding="utf-8"))


def one(records: list[dict], identifier: str) -> dict:
    found = [record for record in records if record.get("id") == identifier]
    assert len(found) == 1, identifier
    return found[0]


def words(text_id: str) -> list[dict]:
    doc = text_document(ROOT, text_id)
    return [word for segment in doc["segments"] for word in segment.get("words", [])]


def forms(text_id: str, first: int, last: int) -> list[str]:
    by_id = {word["id"]: word for word in words(text_id)}
    return [by_id[f"w{number:03d}"]["form"] for number in range(first, last + 1)]


def positions(spans: tuple[tuple[int, int], ...]) -> list[int]:
    return [number for first, last in spans for number in range(first, last + 1)]


def transcript(text_id: str) -> str:
    return (ROOT / "witnesses" / text_id / "mr.txt").read_text(encoding="utf-8")


def headers(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("#")]


def body(text: str) -> list[str]:
    return [line for line in text.splitlines() if line and not line.startswith("#")]


def plain(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def public_record(graph: dict, text_id: str) -> dict:
    return one(bibliography.public_text_evidence(graph)["texts"], text_id)


def test_denominator_is_266_positions():
    assert sum(total for total, _, _ in COUNTS.values()) == 266


@pytest.mark.parametrize("text_id", CLAIMS)
def test_primary_claim_states_what_the_page_prints(data, text_id):
    use = one(data["uses"], f"use.{text_id}.mr1962")
    assert use["claim"] == CLAIMS[text_id]
    assert GENERIC not in use["claim"]
    assert (use["edition"], use["digital_item"], use["role"]) == (EDITION, ITEM, "official_text")
    assert use["address"] == {"kind": "text", "text": text_id}
    assert {key: use[key] for key in PRIMARY[text_id]} == PRIMARY[text_id]


@pytest.mark.parametrize("text_id", CLAIMS)
def test_public_projection_carries_the_exact_claim_and_no_pending_witness(data, text_id):
    record = public_record(data, text_id)
    entries = [entry for group in record["source_groups"] for entry in group["entries"]]
    assert one(entries, f"use.{text_id}.mr1962")["claim"] == CLAIMS[text_id]
    assert record["witnesses"] == []
    assert "collation" not in record


@pytest.mark.parametrize("text_id", SCOPE)
def test_printed_and_supplied_positions_partition_the_reading(text_id):
    ids = [word["id"] for word in words(text_id)]
    printed = positions(SCOPE[text_id]["printed"])
    supplied = positions(SCOPE[text_id]["supplied"])
    assert ids == [f"w{number:03d}" for number in range(1, len(ids) + 1)]
    assert sorted(printed + supplied) == list(range(1, len(ids) + 1))
    assert (len(ids), len(printed), len(supplied)) == COUNTS[text_id]


@pytest.mark.parametrize("text_id", SELECTED)
def test_selected_latin_and_ritual_shape_are_unchanged(text_id):
    assert digest(selected_text(text_document(ROOT, text_id))) == SELECTED[text_id]


def test_confiteor_supplies_only_the_ministers_substitutions(data):
    supplied = [forms(CONFITEOR, first, last) for first, last in SCOPE[CONFITEOR]["supplied"]]
    assert supplied == [["tibi", "pater"], ["te", "pater"]]
    assert set(range(31, 38)) <= set(positions(SCOPE[CONFITEOR]["printed"]))
    assert forms(CONFITEOR, 31, 37) == ["mea", "culpa", "mea", "culpa", "mea", "máxima", "culpa"]
    claim = one(data["uses"], f"use.{CONFITEOR}.mr1962")["claim"]
    assert "with tibi, pater and te, pater in place of vobis, fratres and vos, fratres" in claim
    assert "it is not a second complete printed formula" in claim
    # The threefold mea culpa is printed, so the claim never counts it among supplied words.
    assert "mea culpa" not in claim
    assembly = [line for line in headers(transcript(CONFITEOR)) if line.startswith("# assembly:")]
    assert assembly == [ASSEMBLY[CONFITEOR]]


@pytest.mark.parametrize("text_id", PETITIONS)
def test_domine_non_sum_dignus_is_printed_once_and_repeated(data, text_id):
    first, last = PETITIONS[text_id]
    petition = forms(text_id, first, last)
    assert len(petition) == 17
    assert petition[:4] == ["Dómine", "non", "sum", "dignus"]
    ((start, end),) = SCOPE[text_id]["supplied"]
    assert (start, end - start + 1) == (last + 1, 34)
    assert forms(text_id, start, start + 16) == forms(text_id, start + 17, end) == petition
    claim = one(data["uses"], f"use.{text_id}.mr1962")["claim"]
    assert "one complete Domine, non sum dignus petition" in claim
    assert NOT_PRINTED[text_id] in claim
    assembly = [line for line in headers(transcript(text_id)) if line.startswith("# assembly:")]
    assert assembly == [ASSEMBLY[text_id]]


def test_distribution_formulas_keep_tuam_and_meam_apart(data):
    ecce = one(data["uses"], f"use.{ECCE}.mr1962")["claim"]
    panem = one(data["uses"], f"use.{PANEM}.mr1962")["claim"]
    assert forms(ECCE, 66, 67) == ["ánimam", "tuam"]
    assert forms(PANEM, 65, 66) == ["ánimam", "meam"]
    assert "ending animam tuam" in ecce
    assert "animam meam" not in ecce
    assert "ending animam meam" in panem
    assert "animam tuam" not in panem
    assert body(transcript(ECCE))[-1].endswith("custódiat ánimam tuam in vitam ætérnam. Amen.")
    assert body(transcript(PANEM))[-1].endswith("custódiat ánimam meam in vitam ætérnam. Amen.")


def test_trinity_cues_are_expanded_into_doxology_and_reprise(data):
    assert forms(TRINITY, 26, 45) == DOXOLOGY
    assert forms(TRINITY, 46, 59) == forms(TRINITY, 1, 14)
    doc = text_document(ROOT, TRINITY)
    assert doc["editorial"]["source"]["method"] == TRINITY_METHOD
    rubric = one(doc["segments"], "s04")
    assert rubric["type"] == "rubric"
    assert "repetitur Benedícta" in rubric["text"]
    claim = one(data["uses"], f"use.{TRINITY}.mr1962")["claim"]
    assert "followed by Gloria Patri and Benedicta cues" in claim
    assert "in two halves separated by an Et laudabili refrain" in claim
    assert "not as one uninterrupted Introit formula" in claim


def test_trinity_witness_declares_its_expansion_and_p219_dependency(data):
    mr = one(data["witnesses"], f"witness.{TRINITY}.mr1962")
    assert mr["orthography_profile"] == TRINITY_PROFILE
    assert mr["independence_basis"] == TRINITY_BASIS
    assert mr.get("source_dependencies") == {"uses": [SUPPLEMENT], "raw_binding": None}
    assert source_dependencies(mr) == {"uses": [SUPPLEMENT], "raw_binding": None}
    assert mr["transcription_sha256"] == transcript_digest(transcript(TRINITY))
    bound = witness_subject(ROOT, mr, data, text_document(ROOT, TRINITY))
    assert bound["contract"] == "witness-review-2"
    assert sorted(bound["source_uses"]) == sorted([mr["use"], SUPPLEMENT])
    assert bound["raw_resolution"] is None


def test_trinity_p219_use_is_word_scoped_and_claims_no_performer(data):
    use = one(data["uses"], SUPPLEMENT)
    assert use == SUPPLEMENT_RECORD
    serialized = json.dumps(use, ensure_ascii=False)
    assert [marker for marker in PATH_MARKERS if marker in serialized] == []
    assert use["claim"].endswith("is not evidence for the Trinity Introit’s performer.")
    # Another locus of the same edition is a dependency, not a second witness family.
    assert [w["id"] for w in data["witnesses"] if w["use"] == SUPPLEMENT] == []
    entries = [
        e for group in public_record(data, TRINITY)["source_groups"] for e in group["entries"]
    ]
    assert one(entries, SUPPLEMENT) == {
        "id": SUPPLEMENT,
        "address": {"kind": "word", "word": "w026"},
        "claim": use["claim"],
    }


def test_trinity_keeps_its_historical_p401_locator(data):
    use = one(data["uses"], f"use.{TRINITY}.mr1962")
    assert use["locator"] == PRIMARY[TRINITY]["locator"]
    assert "p. 401" in use["locator"]["printed"]
    assert "leaf n482" in use["locator"]["scan"]
    assert "219" not in json.dumps(use["locator"])
    groups = [
        group
        for group in public_record(data, TRINITY)["source_groups"]
        if any(entry["id"] == use["id"] for entry in group["entries"])
    ]
    assert [group["locator"] for group in groups] == [PRIMARY[TRINITY]["locator"]]


def test_trinity_transcript_keeps_history_and_excludes_the_canticle_refrain():
    text = transcript(TRINITY)
    assert headers(text) == [*HISTORICAL_HEADERS, QUALIFIER]
    lines = text.splitlines()
    first_body = next(i for i, line in enumerate(lines) if line and not line.startswith("#"))
    assert lines[first_body - 1] == QUALIFIER
    verses = body(text)
    assert len(verses) == 4
    assert verses[0] == verses[3]
    assert verses[2] == DOXOLOGY_LINE
    assert "laudabili" not in plain(" ".join(verses))


def test_terra_keeps_its_exclamation_mark():
    (word,) = [word for word in words(TRINITY) if word["id"] == "w025"]
    assert (word["form"], word.get("post")) == ("terra", "!")
    assert body(transcript(TRINITY))[1].endswith("in univérsa terra!")


def test_source_reviews_stay_pending_and_unadmitted(data):
    trinity = sorted(w["id"] for w in data["witnesses"] if w["text"] == TRINITY)
    assert trinity == [f"witness.{TRINITY}.do44667ff", f"witness.{TRINITY}.mr1962"]
    assert all(one(data["witnesses"], i)["review"] == {"status": "pending"} for i in trinity)
    collation = one(data["collations"], f"collation.{TRINITY}.mr1962-do44667ff")
    assert collation["review"] == {"status": "pending"}
    digital = one(data["witnesses"], f"witness.{TRINITY}.do44667ff")
    # The digital witness's inventory is still unknown, not declared empty.
    assert "source_dependencies" not in digital
    with pytest.raises(BindingError, match="complete explicit source_dependencies"):
        witness_subject(ROOT, digital, data, text_document(ROOT, TRINITY))
    ordinary = {CONFITEOR, ECCE, PANEM}
    ordinary_records = {
        key: [r for r in data[key] if r.get("text", r.get("address", {}).get("text")) in ordinary]
        for key in ("uses", "witnesses", "collations")
    }
    historical = before_main_ordo_records(ordinary_records, PANEM)
    ordinary_witnesses = historical["witnesses"]
    assert ordinary_witnesses == [
        {
            "id": "witness.ordinarium.confiteor.handmissal-eo2025",
            "text": "ordinarium.confiteor",
            "use": "use.ordinarium.confiteor.handmissal-eo2025",
            "role": "derived_comparison",
            "coverage": {"kind": "full"},
            "transcription_sha256": (
                "192794ba3fc35fcfa1f33ad8408e5c77a963383ad2f6d4ec1ef19ae520e99d76"
            ),
            "orthography_profile": "exact-typeset-page",
            "independence_basis": (
                "Separately typeset current hand missal, manually compared throughout "
                "the declared Latin body. No genealogical independence or identity with "
                "the unretained August download is claimed."
            ),
            "transcription": "handmissal-eo2025",
            "source_dependencies": {
                "uses": [],
                "raw_binding": None,
                "documents": [
                    {
                        "contract": "paginated-pdf-1",
                        "use": "use.ordinarium.confiteor.handmissal-eo2025",
                        "digital_item": "item.extraordinaryform.handmissal-chant.2025-12-12.pdf",
                        "sha256": (
                            "43e21a0356b4ab1641c8dfa3927d8e29b53f3b26f926b23080842d601e07d84d"
                        ),
                        "media_type": "application/pdf",
                        "pdf_page": 6,
                        "printed": "4",
                        "region": "left-half",
                        "page_image_sha256": (
                            "e554421da2c8241462b4f3d3bf46a64ee1f1a873362ff2623983da81ba3e07fe"
                        ),
                    }
                ],
            },
            "review": {"status": "pending"},
        }
    ]
    # The new pending Panem record must match in full, not merely disappear by id.
    added = one(data["witnesses"], f"witness.{PANEM}.main-ordo-do44667ff")
    saved = deepcopy(added)
    try:
        added["review"] = {"status": "reviewed", "sha256": "0" * 64}
        with pytest.raises(AssertionError, match="complete named main Ordo graph addition"):
            before_main_ordo_records(ordinary_records, PANEM)
    finally:
        added.clear()
        added.update(saved)
        assert added == saved
        assert before_main_ordo_records(ordinary_records, PANEM) == historical
    # A retained source use is not a reviewed witness or a collation approval.
    for text_id in ordinary:
        record = public_record(data, text_id)
        assert record.get("witnesses", []) == []
        assert "collation" not in record
    assert [c["id"] for c in data["collations"] if c["text"] in ordinary] == []
