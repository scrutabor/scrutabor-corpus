"""Keep the damaged Epiphany image distinct from the selected Preface."""

import json
from copy import deepcopy

import pytest

from build_reader import bibliography
from build_reader.bibliography_bindings import BindingError, digest, selected_text, witness_subject
from checks.apparatus import derived_summary
from checks.collate import collate, corpus_tokens, load_witness
from checks.layout import CORPUS
from checks.normalize import substantive

TID = "ordinarium.praefatio-epiphaniae"
FOLDER = CORPUS / "witnesses" / TID
CHOSEN = "cum Ángelis et Archángelis, cum"
VISIBLE = "nus Deus Sábaoth. Pleni sunt cæli"
PAGES = [
    (
        "sung-opening",
        307,
        228,
        "w001",
        "ab402bcd5f486c76235b97450bd3f94c702ce1a2f87baa515ed911f6b1712aec",
    ),
    (
        "sung-continuation",
        308,
        229,
        "w030",
        "f434444228715dd8707f6999d60b3346e27cd9de0122cd962605834e4e29b039",
    ),
]


def graph():
    return json.loads((CORPUS / "bibliography/graph.json").read_text())


def core():
    return json.loads((CORPUS / "texts/ordinarium/praefatio-epiphaniae.json").read_text())


def apparatus():
    return json.loads((FOLDER / "apparatus.json").read_text())


def span(data):
    return next(e for e in data["adjudicated"] if e["class"] == "substantive-span")


def mr_witness(data):
    return next(w for w in data["witnesses"] if w["id"] == f"witness.{TID}.mr1962")


def test_epiphany_transcript_preserves_the_visible_discontinuity():
    _, body = load_witness(FOLDER / "mr.txt")
    assert f"reparávit. Et ídeo {VISIBLE} Thronis" in body
    assert "Angelis" not in body and "Ángelis" not in body
    assert len(body.split()) == 59


def test_epiphany_header_identifies_printing_boundary_and_actual_reread():
    meta, _ = load_witness(FOLDER / "mr.txt")
    assert "Editio iuxta typicam, Benziger Brothers, New York, 1962" in meta["description"]
    assert meta["reread"].startswith("2026-10-04")
    assert "following Sanctus" in meta["boundary"]
    assert "local-archive" not in meta and "recollated" not in meta
    assert "transcribed" not in meta


def test_epiphany_span_quotes_both_exact_sequences():
    entry = span(apparatus())
    assert (entry["at"], entry["through"], entry["ours"]) == ("w039", "w043", CHOSEN)
    assert entry["witnesses"] == {"mr": VISIBLE}
    assert "pp. 228-229" in entry["ruling"] and "p. 229" in entry["ruling"]
    assert "not established" in entry["ruling"]


def test_epiphany_does_not_attribute_an_absent_capital_to_the_damaged_image():
    entry = next(e for e in apparatus()["adjudicated"] if e["at"] == "w040")
    assert entry["class"] == "capital-accent"
    assert entry["witnesses"] == {"do": "Angelis"}


def test_epiphany_apparatus_summary_counts_the_span():
    data = apparatus()
    assert (
        data["summary"]
        == derived_summary(data)
        == {
            "entries": 9,
            "classes": ["capital-accent", "orthography", "punctuation", "substantive-span"],
        }
    )
    assert "witnesses agree on the substantive text" not in data["note"]


def test_epiphany_primary_source_does_not_claim_an_intact_typical_edition():
    use = next(u for u in graph()["uses"] if u["id"] == f"use.{TID}.mr1962")
    assert use["role"] == "direct_approved_print"
    assert use["decision"] == "RETAIN_WITH_CORRECTION"
    assert use["verified_on"] == "2026-09-12"
    assert "discontinuity" in use["claim"] and "hand-position rubric" in use["claim"]
    assert (
        use["evidence_sha256"] == "c971c665b11859fdd1937d9ea5ddd6e307c1bf799529d20e3e9589a742874f1c"
    )


@pytest.mark.parametrize("suffix,leaf,printed,word,page_hash", PAGES)
def test_epiphany_sung_pages_are_bound_separately(suffix, leaf, printed, word, page_hash):
    use = next(u for u in graph()["uses"] if u["id"] == f"use.{TID}.{suffix}.mr1962")
    assert use["address"] == {"kind": "word", "text": TID, "word": word}
    assert use["locator"]["printed"] == f"p. {printed}"
    assert use["locator"]["scan"] == f"leaf n{leaf} / PDF p. {leaf + 1}"
    assert (
        use["locator"]["page_url"]
        == f"https://archive.org/details/missale-romanum-1962/page/n{leaf}/mode/1up"
    )
    assert use["evidence_sha256"] == page_hash
    assert use["edition"] == "edition.missale-romanum.1962-typica"
    assert use["digital_item"] == "item.missale-romanum.1962-typica.ia"
    assert use["role"] == "direct_approved_print" and use["decision"] == "RETAIN"


def test_epiphany_witness_declares_same_edition_dependencies_without_raw_expansion():
    data = graph()
    witness = mr_witness(data)
    assert witness["source_dependencies"] == {
        "uses": sorted(
            [f"use.{TID}.{page[0]}.mr1962" for page in PAGES]
            + [f"use.{TID}.hand-position-rubric.mr1962"]
        ),
        "raw_binding": None,
    }
    assert (
        witness["orthography_profile"] == "exact-page-image-with-declared-substantive-discontinuity"
    )
    subject = witness_subject(CORPUS, witness, data, core())
    assert len(subject["source_uses"]) == 4
    assert subject["raw_resolution"] is None


def test_epiphany_source_reviews_remain_pending_and_unpublished():
    data = graph()
    witnesses = [w for w in data["witnesses"] if w["text"] == TID]
    assert len(witnesses) == 2
    assert all(w["review"] == {"status": "pending"} for w in witnesses)
    collation = next(c for c in data["collations"] if c["text"] == TID)
    assert collation["review"] == {"status": "pending"}
    row = next(r for r in bibliography.public_text_evidence(data)["texts"] if r["id"] == TID)
    assert row["witnesses"] == [] and "collation" not in row


def test_epiphany_canonical_latin_and_ritual_identity_are_unchanged():
    doc = core()
    assert len(corpus_tokens(doc)) == 58
    assert (
        digest(selected_text(doc))
        == "f2d97fe19f19dba5e3af942a94841fb56ef6d57b181ca49b4ca16865b89169ff"
    )
    assert " ".join(word for _, word in corpus_tokens(doc)[38:43]) == CHOSEN


def test_epiphany_full_digital_witness_positively_supports_the_selected_phrase():
    meta, body = load_witness(FOLDER / "do.txt")
    assert meta.get("covers", "") == "" and meta["corrigenda"] == meta["recensions"] == []
    assert len(body.split()) == 58
    assert substantive(" ".join(body.split()[38:43])) == substantive(CHOSEN)


def test_epiphany_collation_counts_one_span_without_changing_transcripts():
    before = {p.name: p.read_bytes() for p in FOLDER.iterdir() if p.is_file()}
    errors, warnings, stats = collate(core(), FOLDER)
    assert errors == warnings == []
    assert stats["words"] == 58 and stats["witnesses"] == 2
    assert stats["substantive_spans"] == stats["substantive_variants"] == 1
    assert before == {p.name: p.read_bytes() for p in FOLDER.iterdir() if p.is_file()}


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ("false-raw-quote", "exact raw witness phrase"),
        ("false-selected-quote", "exact complete source-token"),
        ("missing-span", "SUBSTANTIVE length mismatch"),
        ("overlapping-capital", "overlaps substantive span"),
        ("silently-restored-transcript", "exact raw witness phrase"),
        ("unsupported-selected-phrase", "positive full-witness"),
        ("outside-word", "SUBSTANTIVE"),
    ],
)
def test_epiphany_real_span_mutations_fail_existing_collator(tmp_path, mutation, expected):
    directory = tmp_path / "witnesses"
    directory.mkdir()
    for name in ("mr.txt", "do.txt", "apparatus.json"):
        # Read through the same paths as the positive controls.
        (directory / name).write_bytes((FOLDER / name).read_bytes())
    data = apparatus()
    entry = span(data)
    if mutation == "false-raw-quote":
        entry["witnesses"]["mr"] = VISIBLE.replace("Sábaoth.", "Sábaoth")
    elif mutation == "false-selected-quote":
        entry["ours"] = CHOSEN.replace("Ángelis", "Angelis")
    elif mutation == "missing-span":
        data["adjudicated"].remove(entry)
    elif mutation == "overlapping-capital":
        next(e for e in data["adjudicated"] if e["at"] == "w040")["witnesses"]["mr"] = "Angelis"
    elif mutation == "silently-restored-transcript":
        path = directory / "mr.txt"
        path.write_text(path.read_text().replace(VISIBLE, "cum Angelis et Archángelis, cum"))
    elif mutation == "unsupported-selected-phrase":
        path = directory / "do.txt"
        path.write_text(path.read_text().replace("cum Angelis et Archángelis, cum", VISIBLE))
    elif mutation == "outside-word":
        path = directory / "mr.txt"
        path.write_text(path.read_text().replace("hymnum glóriæ", "canticum glóriæ"))
    (directory / "apparatus.json").write_text(json.dumps(data, ensure_ascii=False))
    errors, _, _ = collate(core(), directory)
    assert any(expected in error for error in errors), errors


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ("missing-use", "unknown source use"),
        ("other-edition", "another edition"),
        ("invalid-address", "unknown word"),
        ("invented-raw-binding", "declared raw binding differs"),
    ],
)
def test_epiphany_dependency_mutations_fail_existing_contract(mutation, expected):
    data = deepcopy(graph())
    witness = mr_witness(data)
    dependency = next(u for u in data["uses"] if u["id"] == f"use.{TID}.sung-continuation.mr1962")
    if mutation == "missing-use":
        data["uses"].remove(dependency)
    elif mutation == "other-edition":
        dependency["edition"] = "edition.divinum-officium-missa.44667ff"
        dependency["digital_item"] = "item.divinum-officium-missa.44667ff.github"
    elif mutation == "invalid-address":
        dependency["address"]["word"] = "w999"
    elif mutation == "invented-raw-binding":
        witness["source_dependencies"]["raw_binding"] = "epiphany-preface"
    with pytest.raises(BindingError, match=expected):
        witness_subject(CORPUS, witness, data, core())


def test_epiphany_retained_accidentals_name_the_actual_approved_printing():
    data = apparatus()
    retained = [
        e
        for e in data["adjudicated"]
        if e["at"] in {"w004", "w017", "w018", "w019", "w046", "w050", "w051"}
    ]
    assert len(retained) == 7
    assert all(e["ruling"].startswith("The approved Benziger printing's ") for e in retained)
    assert not any("The typical edition's" in e["ruling"] for e in data["adjudicated"])
