"""What this edition may reproduce, held as data rather than as a hope.

The corpus cites 52 works. Eight of them are cited for WORDING — a verse
translation that follows what the Church actually prays in that language — and
that is a different kind of citation from a scripture reference or a dictionary
note. A reference says where to look. A wording citation says whose words these
are.

Until 2026-08-18 nothing recorded the difference and nothing recorded rights at
all, while the repository offered the whole corpus under one licence. That is
the shape of a rights incident: not a wrong statement, but no statement, made
about every translated segment at once.

`sources.json` now carries every work with a status — public-domain, own,
permission, unverified — and a basis saying why. This file holds it to the
corpus:

- every title cited anywhere resolves to a work in the registry
- every work carries a status the registry declares
- nothing new can be cited without saying what it is

It does NOT decide whether a use is lawful. `permission` means a living rights
holder and no permission recorded here, and `unverified` means nobody has
established which case applies. Both are facts about this repository. Neither
is a legal opinion, and the count of them is the point: it is meant to be read
and acted on, not to sit at zero.

Since 2026-08-22 the denominator is the translation itself, not its citations.
Every `verse segment × language` site is counted exactly once. Deleting a
citation therefore moves a site to `own`; it cannot make the site disappear.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

STATUSES = ("public-domain", "own", "permission", "unverified")

# A site with several wording sources takes the most restrictive state. An
# unregistered work is stricter still: there is not enough data to classify it.
RESTRICTIVENESS = {
    "own": 0,
    "public-domain": 1,
    "permission": 2,
    "unverified": 3,
    "unregistered": 4,
}

# A citation on a translation names the wording this edition follows. Anywhere
# else it names a place to look, which raises no question of reproduction.
WORDING_FIELD = "translation_citations"

DLIBRA_ITEM = re.compile(r"/dlibra/publication/(?P<publication>\d+)/edition/(?P<edition>\d+)")


def dlibra_identity(url: object) -> tuple[str, str] | None:
    """The two IDs dLibra needs to identify one edition unambiguously."""
    if not isinstance(url, str):
        return None
    match = DLIBRA_ITEM.search(url)
    if match is None:
        return None
    return match.group("publication"), match.group("edition")


def load(corpus: Path) -> tuple[dict, list[str]]:
    path = corpus / "sources.json"
    if not path.exists():
        return {}, ["sources.json is missing — every cited work must declare its rights"]
    doc = json.loads(path.read_text(encoding="utf-8"))
    works = doc.get("works") or {}
    errors = []
    for title, work in sorted(works.items()):
        status = (work.get("rights") or {}).get("status")
        if status not in STATUSES:
            errors.append(f"sources.json:{title}: status {status!r} is not one of {STATUSES}")
        if not ((work.get("rights") or {}).get("basis") or "").strip():
            errors.append(f"sources.json:{title}: a status without a basis says nothing")
        url = work.get("url")
        if isinstance(url, str) and "/dlibra/publication/" in url and "/edition/" not in url:
            errors.append(
                f"sources.json:{title}: a dLibra item URL must identify both the "
                "publication and edition — a bare publication number may belong to "
                "a different record"
            )
    return works, errors


def citation_entries(doc: object, field: str | None = None) -> list[tuple[str, bool, str | None]]:
    """Every (title, is-wording, URL) citation in a document."""
    out: list[tuple[str, bool, str | None]] = []
    if isinstance(doc, dict):
        if "title" in doc and "locator" in doc:
            out.append((doc["title"], field == WORDING_FIELD, doc.get("url")))
        for key, value in doc.items():
            out += citation_entries(value, key if key.endswith("_citations") else field)
    elif isinstance(doc, list):
        for value in doc:
            out += citation_entries(value, field)
    return out


def cited(doc: object, field: str | None = None) -> list[tuple[str, bool]]:
    """Every (title, is-wording) pair in a document."""
    return [(title, wording) for title, wording, _url in citation_entries(doc, field)]


def check(docs: list[dict], works: dict) -> list[str]:
    """One message per citation the registry cannot account for."""
    errors = []
    wording_titles: set[str] = set()
    url_mismatches: set[tuple[str, str, str]] = set()
    for doc in docs:
        for title, wording, url in citation_entries(doc):
            if title not in works:
                errors.append(
                    f"{doc.get('id') or doc.get('text') or '?'}: cites {title!r}, which is "
                    f"not in sources.json — a work this edition quotes must say what it is"
                )
            elif wording:
                wording_titles.add(title)
            work = works.get(title)
            registered_url = work.get("url") if work is not None else None
            if isinstance(url, str) and "/dlibra/publication/" in url:
                if dlibra_identity(url) is None:
                    errors.append(
                        f"citation {title!r}: a dLibra item URL must identify both "
                        "the publication and edition"
                    )
                elif dlibra_identity(registered_url) is not None and dlibra_identity(
                    url
                ) != dlibra_identity(registered_url):
                    assert isinstance(registered_url, str)
                    url_mismatches.add((title, url, registered_url))
    for title, url, registered_url in sorted(url_mismatches):
        errors.append(
            f"citation {title!r}: dLibra edition {url!r} differs from the "
            f"sources.json edition {registered_url!r}"
        )
    flagged = {title for title, work in works.items() if work.get("cited_for_wording") is True}
    for title in sorted(wording_titles - flagged):
        errors.append(
            f"sources.json:{title}: a current translation follows this work, "
            "but cited_for_wording is not true"
        )
    for title in sorted(flagged - wording_titles):
        errors.append(
            f"sources.json:{title}: cited_for_wording is true, but no current "
            "translation cites this work for wording"
        )
    _tally, site_errors = wording_sites(docs, works)
    return errors + site_errors


def wording_sites(docs: list[dict], works: dict) -> tuple[dict[str, int], list[str]]:
    """Classify every translated segment-language site exactly once.

    Each published language layer reaches this check as a self-contained gloss
    document. Such a document has `text`, `lang`, and a segment map;
    Latin documents and lexicon documents do not, and are deliberately ignored
    here while their citations are still registered by :func:`check`.
    """
    tally = {status: 0 for status in (*STATUSES, "unregistered")}
    seen: set[tuple[str, str, str]] = set()
    errors: list[str] = []
    for doc in docs:
        text = doc.get("text")
        lang = doc.get("lang")
        segments = doc.get("segments")
        if not isinstance(text, str) or not isinstance(lang, str) or not isinstance(segments, dict):
            continue
        for segment_id, segment in segments.items():
            if not isinstance(segment, dict) or "translation" not in segment:
                continue
            site = (text, segment_id, lang)
            if site in seen:
                errors.append(f"{'.'.join(site)}: translation site is counted more than once")
                continue
            seen.add(site)
            citations = segment.get(WORDING_FIELD) or []
            statuses = []
            for citation in citations:
                work = works.get(citation.get("title"))
                statuses.append(
                    "unregistered"
                    if work is None
                    else (work.get("rights") or {}).get("status", "unverified")
                )
            status = max(statuses, key=RESTRICTIVENESS.__getitem__) if statuses else "own"
            tally[status] += 1
    return tally, errors


def exposure(docs: list[dict], works: dict) -> dict[str, int]:
    """Compatibility wrapper returning the complete per-site tally."""
    tally, _errors = wording_sites(docs, works)
    return tally
