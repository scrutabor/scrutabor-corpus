"""One work must not reach the bibliography under two titles."""

from checks.citations import check, key


def cite(title):
    return {"citations": [{"title": title, "locator": "s.v. x"}]}


def test_two_spellings_of_one_work_are_an_error():
    docs = [cite("Lewis and Short, A Latin Dictionary"), cite("Lewis–Short, A Latin Dictionary")]
    errors = check(docs)
    assert len(errors) == 1
    assert "2 titles" in errors[0]
    # The message must name both, so the fix is a choice and not a search.
    assert "Lewis and Short" in errors[0] and "Lewis–Short" in errors[0]


def test_one_spelling_is_silent():
    docs = [cite("Lewis and Short, A Latin Dictionary")] * 3
    assert check(docs) == []


def test_genuinely_different_works_are_silent():
    docs = [
        cite("Liddell–Scott–Jones, A Greek–English Lexicon"),
        cite("Brown–Driver–Briggs, A Hebrew and English Lexicon"),
        cite("Lewis and Short, A Latin Dictionary"),
    ]
    assert check(docs) == []


def test_key_ignores_only_what_may_vary():
    assert key("Lewis and Short, A Latin Dictionary") == key("Lewis–Short, A Latin Dictionary")
    assert key("Missale Romanum (1962)") != key("Missale Romanum (1920)")


def test_a_bare_title_with_no_locator_is_not_a_citation():
    # `title` is a common key. Only a citation carries a locator or a url.
    bare = {"title": "Lewis–Short, A Latin Dictionary"}
    assert check([bare, cite("Lewis and Short, A Latin Dictionary")]) == []
