"""Opt-in typeset-PDF identity assertions, never automatic visual verification."""

from copy import deepcopy

PDF_SHA = "43e21a0356b4ab1641c8dfa3927d8e29b53f3b26f926b23080842d601e07d84d"
PAGE_SHA = "e554421da2c8241462b4f3d3bf46a64ee1f1a873362ff2623983da81ba3e07fe"
COMMON_PAGE_SHA = "81210742f30a43cf67289f1911557fac6e052b800304533b82d51a7658fe7187"
SUPPORTED_PAGES = {
    (
        "ordinarium.confiteor-sacerdotis",
        4,
        "2",
        "left-half",
    ): "6f1ce1f0e66649f05c65f1f82c556dd5ab4bca009c315f7c5805e66c34bb59bf",
    (
        "ordinarium.confiteor",
        6,
        "4",
        "left-half",
    ): "e554421da2c8241462b4f3d3bf46a64ee1f1a873362ff2623983da81ba3e07fe",
    (
        "ordinarium.evangelium-ultimum",
        28,
        "26",
        "left-half",
    ): "35e0cbcd059bd4c45036267a76cbec2b7b4adb3cdab22f219b8bb6ed5ac98262",
    ("ordinarium.aufer-a-nobis", 6, "4", "left-half"): PAGE_SHA,
    ("ordinarium.praefatio-communis", 16, "14", "left-half"): COMMON_PAGE_SHA,
}

URL = "https://extraordinaryform.org/handmissals/HandMissalChant.pdf"
FIELDS = {
    "contract",
    "use",
    "digital_item",
    "sha256",
    "media_type",
    "pdf_page",
    "printed",
    "region",
    "page_image_sha256",
}


def declarations(value):
    """Only an explicit nonempty inventory opts in; old subjects acquire no key."""
    if not isinstance(value, list) or not value:
        raise ValueError("paginated documents require a nonempty explicit inventory")
    identifiers = []
    for record in value:
        if not isinstance(record, dict) or set(record) != FIELDS:
            raise ValueError("paginated document declaration has unexpected fields")
        if not isinstance(record["use"], str) or not record["use"]:
            raise ValueError("paginated document requires an exact use ID")
        identifiers.append(record["use"])
    if identifiers != sorted(set(identifiers)):
        raise ValueError("paginated document use IDs must be sorted and unique")
    return deepcopy(value)


def resolve_documents(value, sources):
    """Bind the first supported manifestation; do not whitelist other PDFs."""
    records = declarations(value)
    if {r["use"] for r in records} != set(sources):
        raise ValueError("paginated documents must exactly inventory non-DO born-digital uses")
    resolved = {}
    for record in records:
        source = sources[record["use"]]
        use, item = source["use"], source["digital_item"]
        page_key = (
            use.get("address", {}).get("text"),
            record["pdf_page"],
            record["printed"],
            record["region"],
        )
        if (
            record["contract"] != "paginated-pdf-1"
            or record["media_type"] != "application/pdf"
            or type(record["pdf_page"]) is not int
            or record["sha256"] != PDF_SHA
            or not any(
                page_key == key and record["page_image_sha256"] == page_sha
                for key, page_sha in SUPPORTED_PAGES.items()
            )
        ):
            raise ValueError("paginated document differs from the supported typeset PDF and page")
        if (
            item["kind"] != "born-digital"
            or item.get("sha256") != record["sha256"]
            or item["id"] != record["digital_item"]
            or item.get("record_url") != URL
            or use.get("evidence_sha256") != record["page_image_sha256"]
            or use.get("role") != "corroborating_latin_witness"
            or not isinstance(use.get("locator", {}).get("section"), str)
            or not use["locator"]["section"].strip()
        ):
            raise ValueError("paginated document source-use/item identity differs")
        resolved[record["use"]] = deepcopy(record)
    return {"contract": "paginated-document-inventory-1", "documents": resolved}
