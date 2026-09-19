"""Exact phrase rulings must not weaken full-witness collation."""

from copy import deepcopy

import pytest
from test_collate import a_text, witnesses

from checks.collate import collate

CHOSEN = "famulórum famularúmque tuárum"
OTHER = "fratrum, propinquórum et benefactórum nostrórum"
CANONICAL = f"animas {CHOSEN} absolve."
ALTERNATE = f"animas {OTHER} absolve."


def ruling(at="w002", through="w004", ours=CHOSEN, reading=OTHER, wid="b"):
    return {
        "at": at,
        "through": through,
        "ours": ours,
        "witnesses": {wid: reading},
        "class": "substantive-span",
        "ruling": "Retain the complete reading attested here by the other full witness.",
    }


def check(tmp_path, *, doc=None, pages=None, entries=None):
    return collate(
        doc or a_text(*CANONICAL.split()),
        witnesses(
            tmp_path,
            pages or {"a": CANONICAL, "b": ALTERNATE},
            [ruling()] if entries is None else entries,
        ),
    )


def test_a_longer_exact_phrase_is_counted_without_modifying_the_witness(tmp_path):
    directory = witnesses(tmp_path, {"a": CANONICAL, "b": ALTERNATE}, [ruling()])
    before = {path.name: path.read_bytes() for path in directory.iterdir()}
    errors, warnings, stats = collate(a_text(*CANONICAL.split()), directory)
    assert errors == warnings == []
    assert stats["substantive_variants"] == stats["substantive_spans"] == 1
    assert stats["words"] == 5
    assert stats["witnesses"] == 2
    assert stats["orthographic"] == stats["omissions"] == 0
    assert before == {path.name: path.read_bytes() for path in directory.iterdir()}


@pytest.mark.parametrize("reading", ["fratrum nostrórum", "fratrum propinquórum nostrórum"])
def test_shorter_and_equal_length_phrases_are_supported(tmp_path, reading):
    errors, _, stats = check(
        tmp_path,
        pages={"a": CANONICAL, "b": f"animas {reading} absolve."},
        entries=[ruling(reading=reading)],
    )
    assert errors == []
    assert stats["substantive_spans"] == 1


def test_one_to_many_and_many_to_one_readings_are_explicit(tmp_path):
    doc = a_text("a", "b", "c", "d")
    entries = [ruling("w002", "w002", "b", "e f"), ruling("w003", "w004", "c d", "g")]
    errors, _, stats = check(
        tmp_path, doc=doc, pages={"a": "a b c d", "b": "a e f g"}, entries=entries
    )
    assert errors == []
    assert stats["substantive_spans"] == 2


def test_range_follows_document_order_not_the_numeric_word_ids(tmp_path):
    doc = a_text("ut", "animas", "famulorum", "famularumque", "tuarum,", "quae", "requiescunt")
    for word, word_id in zip(
        doc["segments"][0]["words"],
        ["w013", "w060", "w061", "w062", "w063", "w018", "w019"],
        strict=True,
    ):
        word["id"] = word_id
    ours = "animas famulorum famularumque tuarum, quae"
    reading = "nostrae congregationis fratres, propinquos et benefactores, qui"
    errors, _, _ = check(
        tmp_path,
        doc=doc,
        pages={"a": f"ut {ours} requiescunt", "b": f"ut {reading} requiescunt"},
        entries=[ruling("w060", "w018", ours, reading)],
    )
    assert errors == []


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("at", "w999", "existing words"),
        ("through", "w999", "existing words"),
        ("through", None, "existing words"),
        ("through", [], "existing words"),
        ("through", "w001", "backwards"),
        ("ours", CHOSEN + ",", "exact complete"),
        ("ours", "famulorum famularumque tuarum", "exact complete"),
        ("ruling", " ", "nonempty ruling"),
        ("ruling", None, "nonempty ruling"),
    ],
)
def test_malformed_span_fails_closed(tmp_path, field, value, message):
    entry = ruling()
    entry[field] = value
    errors, _, _ = check(tmp_path, entries=[entry])
    assert any(message in error for error in errors)


@pytest.mark.parametrize("reading", ["", " ", "--", "fratres  nostri", "fratres --", "fra-tres"])
def test_invalid_reading_sequences_are_rejected(tmp_path, reading):
    errors, _, _ = check(tmp_path, entries=[ruling(reading=reading)])
    assert any("exact word sequence" in error for error in errors)


@pytest.mark.parametrize("reading", [CHOSEN, CHOSEN + ",", "FAMULORUM famularumque tuarum"])
def test_identical_or_accidental_only_spans_are_not_substantive(tmp_path, reading):
    errors, _, _ = check(
        tmp_path,
        pages={"a": CANONICAL, "b": f"animas {reading} absolve."},
        entries=[ruling(reading=reading)],
    )
    assert any("redundant or accidental-only" in error for error in errors)


@pytest.mark.parametrize("quoted", [OTHER.replace(",", ""), OTHER + " extra", "fratrum nostrorum"])
def test_the_alternate_quote_must_match_the_actual_raw_phrase(tmp_path, quoted):
    errors, _, _ = check(tmp_path, entries=[ruling(reading=quoted)])
    assert any("exact raw witness phrase at this locus" in error for error in errors)


def test_internal_free_standing_punctuation_is_part_of_the_exact_quote(tmp_path):
    reading = OTHER.replace(" et ", " — et ")
    errors, _, _ = check(
        tmp_path,
        pages={"a": CANONICAL, "b": f"animas {reading} absolve."},
        entries=[ruling(reading=reading)],
    )
    assert errors == []
    errors, _, _ = check(tmp_path, pages={"a": CANONICAL, "b": f"animas {reading} absolve."})
    assert any("exact raw witness phrase" in error for error in errors)


@pytest.mark.parametrize("position", ["before", "after"])
@pytest.mark.parametrize("kind", ["punctuation", "substantive", "extra-word"])
def test_a_span_never_hides_unruled_surrounding_differences(tmp_path, position, kind):
    tokens = ALTERNATE.split()
    index = 0 if position == "before" else -1
    if kind == "punctuation":
        tokens[index] += ","
    elif kind == "substantive":
        tokens[index] = "aliter"
    else:
        tokens.insert(0 if position == "before" else len(tokens), "extra")
    errors, _, _ = check(tmp_path, pages={"a": CANONICAL, "b": " ".join(tokens)})
    assert errors


def test_surrounding_accidentals_and_spelling_keep_their_separate_rulings(tmp_path):
    doc = a_text("Animas,", *CHOSEN.split(), "iudica.")
    entries = [ruling()]
    entries.extend(
        [
            {"at": "w001", "ours": "Animas,", "witnesses": {"b": "Animas"}, "class": "punctuation"},
            {
                "at": "w005",
                "ours": "iudica.",
                "witnesses": {"b": "judica."},
                "class": "orthography",
                "ruling": "Retain consonantal i.",
            },
        ]
    )
    errors, _, stats = check(
        tmp_path,
        doc=doc,
        pages={"a": f"Animas, {CHOSEN} iudica.", "b": f"Animas {OTHER} judica."},
        entries=entries,
    )
    assert errors == []
    assert stats["variants_adjudicated"] == stats["orthographic"] == stats["substantive_spans"] == 1


def test_overlapping_spans_are_rejected_even_for_different_witnesses(tmp_path):
    entries = [
        ruling(),
        ruling("w003", "w005", "famularúmque tuárum absolve.", "alios libera", "a"),
    ]
    errors, _, _ = check(tmp_path, entries=entries)
    assert any("overlapping substantive spans" in error for error in errors)


def test_overlapping_word_ruling_is_not_swallowed(tmp_path):
    entries = [
        ruling(),
        {"at": "w003", "ours": "famularúmque", "witnesses": {"b": "et"}, "class": "substantive"},
    ]
    errors, _, _ = check(tmp_path, entries=entries)
    assert any("overlaps substantive span" in error for error in errors)


def test_a_separate_witness_can_have_an_accidental_inside_the_selected_span(tmp_path):
    pages = {"a": CANONICAL.replace("famulórum", "famulorum"), "b": ALTERNATE}
    entries = [
        ruling(),
        {"at": "w002", "ours": "famulórum", "witnesses": {"a": "famulorum"}, "class": "accent"},
    ]
    errors, _, _ = check(tmp_path, pages=pages, entries=entries)
    assert errors == []


@pytest.mark.parametrize(
    "pages", [{"a": ALTERNATE, "b": ALTERNATE}, {"a": CANONICAL, "b": CANONICAL}]
)
def test_unsupported_or_stale_ruling_fails(tmp_path, pages):
    errors, _, _ = check(tmp_path, pages=pages)
    assert any(
        "positive full-witness" in error or "exact raw witness phrase" in error for error in errors
    )
    assert any("stale ruling" in error for error in errors)


def test_unknown_witness_is_an_unmatched_ruling(tmp_path):
    errors, _, _ = check(tmp_path, entries=[ruling(wid="missing")])
    assert any("w002/missing" in error and "stale ruling" in error for error in errors)


def test_partial_witness_cannot_provide_positive_support(tmp_path):
    entry = ruling()
    entry["witnesses"]["a"] = OTHER
    pages = {"a": ALTERNATE, "b": ALTERNATE, "c": f"# covers: w002-w004\n{CHOSEN}"}
    errors, _, _ = check(tmp_path, pages=pages, entries=[entry])
    assert any("positive full-witness" in error for error in errors)


def test_one_witness_must_attest_the_entire_phrase_not_a_union_of_readings(tmp_path):
    pages = {
        "a": CANONICAL.replace("tuárum", "nostrarum"),
        "b": ALTERNATE,
        "c": CANONICAL.replace("famulórum", "fratrum"),
    }
    errors, _, _ = check(tmp_path, pages=pages)
    assert any("positive full-witness" in error for error in errors)


def test_a_chosen_phrase_later_in_the_witness_does_not_support_this_locus(tmp_path):
    pages = {"a": f"animas alios {CHOSEN}", "b": ALTERNATE}
    errors, _, _ = check(tmp_path, pages=pages)
    assert any("positive full-witness" in error for error in errors)


def test_no_search_for_an_alternate_phrase_later_on_the_page(tmp_path):
    errors, _, _ = check(tmp_path, pages={"a": CANONICAL, "b": f"animas extra {OTHER} absolve."})
    assert any("exact raw witness phrase at this locus" in error for error in errors)


def test_corrigendum_cannot_manufacture_positive_support(tmp_path):
    pages = {
        "a": "# corrigendum: fratrum -> famulórum (printing slip)\n"
        + CANONICAL.replace("famulórum", "fratrum"),
        "b": ALTERNATE,
    }
    errors, _, _ = check(tmp_path, pages=pages)
    assert any("positive full-witness" in error for error in errors)


def test_corrigendum_cannot_manufacture_the_quoted_alternate(tmp_path):
    pages = {
        "a": CANONICAL,
        "b": "# corrigendum: aliorum -> fratrum (printing slip)\n"
        + ALTERNATE.replace("fratrum,", "aliorum,"),
    }
    errors, _, _ = check(tmp_path, pages=pages)
    assert any("exact raw witness phrase" in error for error in errors)


def test_circular_span_replacements_cannot_supply_evidence(tmp_path):
    entry = ruling()
    entry["witnesses"]["a"] = OTHER
    errors, _, _ = check(tmp_path, pages={"a": ALTERNATE, "b": ALTERNATE}, entries=[entry])
    assert sum("positive full-witness" in error for error in errors) == 2


def test_balanced_length_changes_cannot_create_ordinal_support(tmp_path):
    # Witness a happens to print the chosen phrase at the same raw index,
    # but its declared earlier expansion and later contraction shift loci.
    doc = a_text("a", "b", "c", "d", "e", "f", "g")
    entries = [
        ruling("w001", "w001", "a", "h i", "a"),
        ruling("w003", "w004", "c d", "j", "a"),
        ruling("w005", "w006", "e f", "k l", "b"),
    ]
    pages = {"a": "h i b j e f g", "b": "a b c d k l g"}
    errors, _, _ = check(tmp_path, doc=doc, pages=pages, entries=entries)
    assert any(
        "b: substantive span at w005 has no positive full-witness" in error for error in errors
    )


@pytest.mark.parametrize("before", [True, False])
def test_separate_omission_can_be_aligned_without_losing_span_or_outside_checks(tmp_path, before):
    tokens = CANONICAL.split()
    omitted = "w001" if before else "w005"
    other_tokens = ALTERNATE.split()[1:] if before else ALTERNATE.split()[:-1]
    omission = {
        "at": omitted,
        "ours": tokens[0 if before else -1],
        "witnesses": {"b": ""},
        "class": "omission",
        "ruling": "Retain the word attested in full witness a.",
    }
    errors, _, stats = check(
        tmp_path, pages={"a": CANONICAL, "b": " ".join(other_tokens)}, entries=[ruling(), omission]
    )
    assert errors == []
    assert stats["omissions"] == stats["substantive_spans"] == 1


def test_header_recension_removals_with_span_are_explicitly_unsupported(tmp_path):
    pages = {"a": CANONICAL, "b": f"# recension: -Amen (other recension)\n{ALTERNATE} Amen"}
    errors, _, _ = check(tmp_path, pages=pages)
    assert any("cannot be aligned with header recension removals" in error for error in errors)


def test_partial_alternate_must_cover_the_whole_declared_span(tmp_path):
    pages = {"a": CANONICAL, "b": CANONICAL, "c": f"# covers: w002-w003\n{OTHER}"}
    errors, _, _ = check(tmp_path, pages=pages, entries=[ruling(wid="c")])
    assert any("outside declared witness coverage" in error for error in errors)


def test_a_partial_alternate_adds_evidence_but_does_not_replace_full_witnesses(tmp_path):
    pages = {"a": CANONICAL, "b": CANONICAL, "c": f"# covers: w002-w004\n{OTHER}"}
    errors, _, stats = check(tmp_path, pages=pages, entries=[ruling(wid="c")])
    assert errors == []
    assert stats["witnesses"] == 2 and stats["partial"] == 1
    del pages["b"]
    # Use another fixture directory so the removed file cannot remain.
    directory = tmp_path / "one-full"
    directory.mkdir()
    errors, _, _ = check(directory, pages=pages, entries=[ruling(wid="c")])
    assert any("only 1 full witness" in error for error in errors)


def test_substantive_only_profile_does_not_bypass_exact_span_quotes(tmp_path):
    pages = {
        "a": CANONICAL,
        "b": f"# profile: substantive-only\n{ALTERNATE.replace('fratrum,', 'fratrum')}",
    }
    errors, _, _ = check(tmp_path, pages=pages)
    assert any("exact raw witness phrase" in error for error in errors)


def test_duplicate_span_entries_are_rejected(tmp_path):
    entry = ruling()
    errors, _, _ = check(tmp_path, entries=[entry, deepcopy(entry)])
    assert any("duplicate reading" in error for error in errors)


def test_one_range_can_quote_several_alternate_witnesses(tmp_path):
    entry = ruling()
    entry["witnesses"]["c"] = "fratrum nostrorum"
    pages = {"a": CANONICAL, "b": ALTERNATE, "c": "animas fratrum nostrorum absolve."}
    errors, _, stats = check(tmp_path, pages=pages, entries=[entry])
    assert errors == []
    assert stats["substantive_spans"] == 2


def test_canonical_post_punctuation_is_included_in_ours(tmp_path):
    doc = a_text("animas", "famulórum", "famularúmque", "tuárum", "absolve")
    doc["segments"][0]["words"][3]["post"] = ","
    doc["segments"][0]["words"][4]["post"] = "."
    pages = {"a": CANONICAL.replace("tuárum", "tuárum,"), "b": ALTERNATE}
    errors, _, _ = check(tmp_path, doc=doc, pages=pages, entries=[ruling(ours=CHOSEN + ",")])
    assert errors == []
    errors, _, _ = check(tmp_path, doc=doc, pages=pages)
    assert any("exact complete source-token" in error for error in errors)


def test_unsupported_or_inaccurate_omission_alongside_span_is_rejected(tmp_path):
    omission = {
        "at": "w001",
        "ours": "alios",
        "witnesses": {"b": ""},
        "class": "omission",
        "ruling": "A false selected quote.",
    }
    errors, _, _ = check(
        tmp_path,
        pages={"a": CANONICAL, "b": " ".join(ALTERNATE.split()[1:])},
        entries=[ruling(), omission],
    )
    assert any("invalid or unsupported omission" in error for error in errors)


def test_an_outside_corrigendum_keeps_its_existing_behavior(tmp_path):
    pages = {
        "a": CANONICAL,
        "b": "# corrigendum: absove -> absolve (printing slip)\n"
        + ALTERNATE.replace("absolve.", "absove."),
    }
    errors, _, stats = check(tmp_path, pages=pages)
    assert errors == []
    assert stats["corrigenda"] == stats["substantive_spans"] == 1


def test_an_outside_substantive_variant_still_requires_its_own_positive_support(tmp_path):
    entry = {
        "at": "w005",
        "ours": "absolve.",
        "witnesses": {"b": "libera."},
        "class": "substantive",
        "ruling": "Retain the other full witness's verb.",
    }
    errors, _, stats = check(
        tmp_path,
        pages={"a": CANONICAL, "b": ALTERNATE.replace("absolve.", "libera.")},
        entries=[ruling(), entry],
    )
    assert errors == []
    assert stats["substantive_variants"] == 2 and stats["substantive_spans"] == 1


def test_legacy_one_word_class_cannot_authorize_a_phrase(tmp_path):
    entry = ruling()
    entry["class"] = "substantive"
    errors, _, _ = check(tmp_path, entries=[entry])
    assert any("SUBSTANTIVE length mismatch" in error for error in errors)


def test_unruled_phrase_length_change_still_fails(tmp_path):
    errors, _, _ = check(tmp_path, entries=[])
    assert any("SUBSTANTIVE length mismatch" in error for error in errors)


def test_a_ruling_does_not_skip_an_unlisted_differing_witness(tmp_path):
    errors, _, _ = check(tmp_path, pages={"a": CANONICAL, "b": ALTERNATE, "c": ALTERNATE})
    assert any("c: SUBSTANTIVE length mismatch" in error for error in errors)


def test_other_apparatus_entries_cannot_manufacture_positive_support(tmp_path):
    pages = {"a": CANONICAL.replace("famulórum", "famulorumque"), "b": ALTERNATE}
    entries = [
        ruling(),
        {
            "at": "w002",
            "ours": "famulórum",
            "witnesses": {"a": "famulorumque"},
            "class": "orthography",
            "ruling": "A substitution is not raw attestation.",
        },
    ]
    errors, _, _ = check(tmp_path, pages=pages, entries=entries)
    assert any(
        "b: substantive span at w002 has no positive full-witness" in error for error in errors
    )
