"""Exact 177-word VI Epiphany epistle, not a synthetic agreement of witnesses.

MR1962, printed p.416, scan leaf 497, prints the sacred parenthetical clause.
Divinum Officium Missa revision 44667ff, Latin/Tempora/Epi6-0.txt [Lectio],
omits its marks and has twelve other accidental/orthographic differences.
These are collation fixtures, not new selected corpus data or parse approvals.
"""

from copy import deepcopy

import pytest
from test_collate import a_text, witnesses

from build_reader.emit import Table, core_artifact, expand
from checks.collate import collate, corpus_tokens

MR = (
    "Fratres: Grátias ágimus Deo semper pro ómnibus vobis, memóriam vestri faciéntes in "
    "oratiónibus nostris sine intermissióne, mémores óperis fídei vestræ, et labóris, et "
    "caritátis, et sustinéntiæ spei Dómini nostri Iesu Christi, ante Deum et Patrem nostrum: "
    "sciéntes fratres, dilécti a Deo, electiónem vestram: quia Evangélium nostrum non fuit ad "
    "vos in sermóne tantum, sed et in virtúte, et in Spíritu Sancto, et in plenitúdine multa, "
    "sicut scitis quales fuérimus in vobis propter vos. Et vos imitatóres nostri facti estis, "
    "et Dómini, excipiéntes verbum in tribulatióne multa, cum gáudio Spíritus Sancti: ita ut "
    "facti sitis forma ómnibus credéntibus in Macedónia, et in Acháia. A vobis enim diffamátus "
    "est sermo Dómini, non solum in Macedónia, et in Acháia, sed et in omni loco fides vestra, "
    "quæ est ad Deum, profécta est, ita ut non sit nobis necésse quidquam loqui. Ipsi enim de "
    "nobis annúntiant qualem intróitum habuérimus ad vos: et quómodo convérsi estis ad Deum a "
    "simulácris, servíre Deo vivo, et vero, et exspectáre Fílium eius de cælis (quem suscitávit "
    "ex mórtuis) Iesum, qui erípuit nos ab ira ventúra."
)
DO = (
    "Fratres: Grátias ágimus Deo semper pro ómnibus vobis, memóriam vestri faciéntes in "
    "oratiónibus nostris sine intermissióne, mémores óperis fídei vestræ, et labóris, et "
    "caritátis, et sustinéntiæ spei Dómini nostri Jesu Christi, ante Deum et Patrem nostrum: "
    "sciéntes, fratres, dilécti a Deo. electiónem vestram: quia Evangélium nostrum non fuit ad "
    "vos in sermóne tantum, sed et in virtúte, et in Spíritu Sancto, et in plenitúdine multa, "
    "sicut scitis quales fuérimus in vobis propter vos. Et vos imitatóres nostri facti estis, "
    "et Dómini, excipiéntes verbum in tribulatióne multa, cum gáudio Spíritus Sancti: ita ut "
    "facti sitis forma ómnibus credéntibus in Macedónia et in Achája. A vobis enim diffamátus "
    "est sermo Dómini, non solum in Macedónia et in Achája, sed et in omni loco fides vestra, "
    "quæ est ad Deum, profécta est, ita ut non sit nobis necésse quidquam loqui. Ipsi enim de "
    "nobis annúntiant, qualem intróitum habuérimus ad vos: et quómodo convérsi estis ad Deum a "
    "simulácris, servíre Deo vivo et vero, et exspectáre Fílium ejus de cœlis quem suscitávit "
    "ex mórtuis Jesum, qui erípuit nos ab ira ventúra."
)
# Exact positive readings, not a generated permission to accept every mismatch.
READINGS = [
    (30, "Iesu", "Jesu", "orthography"),
    (37, "sciéntes", "sciéntes,", "punctuation"),
    (41, "Deo,", "Deo.", "punctuation"),
    (99, "Macedónia,", "Macedónia", "punctuation"),
    (102, "Acháia.", "Achája.", "orthography"),
    (113, "Macedónia,", "Macedónia", "punctuation"),
    (116, "Acháia,", "Achája,", "orthography"),
    (142, "annúntiant", "annúntiant,", "punctuation"),
    (158, "vivo,", "vivo", "punctuation"),
    (164, "eius", "ejus", "orthography"),
    (166, "cælis", "cœlis", "orthography"),
    (167, "(quem", "quem", "punctuation"),
    (170, "mórtuis)", "mórtuis", "punctuation"),
    (171, "Iesum,", "Jesum,", "orthography"),
]


def selected():
    # Decode this one reviewed transcription into fixture words. This is not
    # a source-framing normalizer and must not strip unknown raw parentheses.
    bare = MR.replace("(quem", "quem").replace("mórtuis)", "mórtuis").split()
    assert len(bare) == 177
    doc = a_text(*(token.rstrip(",.;:?!") for token in bare))
    for word, token in zip(doc["segments"][0]["words"], bare, strict=True):
        if token[-1] in ",.;:?!":
            word["post"] = token[-1]
    doc["segments"][0]["parentheses"] = [{"from": "w167", "through": "w170"}]
    return doc


def apparatus():
    return [
        {
            "at": f"w{position:03d}",
            "ours": printed,
            "witnesses": {"do": digital},
            "class": category,
            "ruling": "Retain the exact MR1962 reading; the digital witness differs at this locus.",
        }
        for position, printed, digital, category in READINGS
    ]


def test_actual_complete_sources_collate_with_truthful_separate_pair_rulings(tmp_path):
    doc = selected()
    before = deepcopy(doc)
    assert " ".join(token for _, token in corpus_tokens(doc)) == MR
    assert len(MR.split()) == len(DO.split()) == 177
    assert "(quem suscitávit ex mórtuis)" in MR
    assert "quem suscitávit ex mórtuis" in DO and "(" not in DO
    directory = witnesses(tmp_path, {"mr1962": MR, "do": DO}, apparatus())
    original_files = {path.name: path.read_bytes() for path in directory.iterdir()}
    errors, warnings, stats = collate(doc, directory)
    assert errors == warnings == []
    assert stats["words"] == 177 and stats["witnesses"] == 2
    assert stats["variants_adjudicated"] == 8 and stats["orthographic"] == 6
    assert stats["omissions"] == stats["substantive_variants"] == 0
    assert original_files == {path.name: path.read_bytes() for path in directory.iterdir()}
    assert doc == before


@pytest.mark.parametrize("position", [167, 170])
def test_either_missing_parenthesis_ruling_fails(tmp_path, position):
    entries = [row for row in apparatus() if row["at"] != f"w{position:03d}"]
    errors, _, _ = collate(selected(), witnesses(tmp_path, {"mr1962": MR, "do": DO}, entries))
    assert any("UNADJUDICATED variant" in error for error in errors)


@pytest.mark.parametrize("mutation", ["remove", "move-open", "move-close", "omit-source-close"])
def test_erasing_moving_or_falsely_transcribing_a_mark_fails(tmp_path, mutation):
    doc = selected()
    printed = MR
    if mutation == "remove":
        del doc["segments"][0]["parentheses"]
    elif mutation == "move-open":
        doc["segments"][0]["parentheses"][0]["from"] = "w168"
    elif mutation == "move-close":
        doc["segments"][0]["parentheses"][0]["through"] = "w169"
    else:
        printed = MR.replace("mórtuis)", "mórtuis")
    assert collate(doc, witnesses(tmp_path, {"mr1962": printed, "do": DO}, apparatus()))[0]


def test_all_177_words_and_exact_surface_survive_real_reader_codec():
    core = selected()
    core.update(
        status="draft",
        analysis_defaults={"confidence": "medium", "review": "pending", "sources": []},
    )
    tables = [Table(), Table(), Table()]
    artifact = core_artifact(core, core, *tables)
    language = {"language": "en", "about": "", "seg": [{"id": "s01", "g": [None] * 177}]}
    expanded, _ = expand(artifact, language, *(table.order for table in tables), [])
    assert expanded["segments"][0]["words"] == core["segments"][0]["words"]
    assert " ".join(token for _, token in corpus_tokens(expanded)) == MR
