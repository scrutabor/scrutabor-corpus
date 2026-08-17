"""A stranded Polish preposition is voiced by the gloss that follows it."""

from checks.vocalised import check, wants_vocalised


def pair(first_gloss, second_gloss, lang="pl"):
    doc = {
        "id": "t",
        "segments": [
            {"id": "s01", "words": [{"id": "w1", "form": "a"}, {"id": "w2", "form": "b"}]}
        ],
    }
    gloss = {"lang": lang, "words": {"w1": {"gloss": first_gloss}, "w2": {"gloss": second_gloss}}}
    return doc, gloss


def test_the_defect_the_owner_found():
    errors = check(*pair("niech szydzą z", "mnie"))
    assert len(errors) == 1
    assert "ze" in errors[0] and "mnie" in errors[0]


def test_w_before_mnie_and_wszystkich():
    assert check(*pair("w", "mnie"))
    assert check(*pair("w", "wszystkich"))


def test_the_vocalised_form_is_silent():
    assert check(*pair("niech szydzą ze", "mnie")) == []
    assert check(*pair("we", "wszystkich")) == []


def test_an_ordinary_cluster_is_not_touched():
    # z domu, w domu: the bare form is right and must not be flagged, or the
    # check becomes noise and gets switched off.
    assert check(*pair("z", "domu")) == []
    assert check(*pair("w", "domu")) == []
    assert check(*pair("z", "Bogiem")) == []


def test_only_polish():
    assert check(*pair("with", "me", lang="en")) == []


def test_the_rule_itself():
    assert wants_vocalised("z", "mnie") and wants_vocalised("z", "mną")
    assert wants_vocalised("z", "słowami") and wants_vocalised("z", "świętym")
    assert wants_vocalised("w", "wszystkich") and wants_vocalised("w", "Mszy")
    assert not wants_vocalised("z", "domu")
    assert not wants_vocalised("z", "sercem")  # s + vowel: bare form is right


def test_a_preposition_mid_gloss_is_not_the_seam():
    # Only a TRAILING preposition meets the next cell.
    assert check(*pair("z domu", "mnie")) == []
