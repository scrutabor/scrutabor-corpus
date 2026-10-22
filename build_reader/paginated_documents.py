"""Opt-in typeset-PDF identity assertions, never automatic visual verification."""

from copy import deepcopy

PDF_SHA = "43e21a0356b4ab1641c8dfa3927d8e29b53f3b26f926b23080842d601e07d84d"
PAGE_SHA = "e554421da2c8241462b4f3d3bf46a64ee1f1a873362ff2623983da81ba3e07fe"
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
        if (
            record["contract"] != "paginated-pdf-1"
            or record["media_type"] != "application/pdf"
            or type(record["pdf_page"]) is not int
            or record["pdf_page"] != 6
            or record["printed"] != "4"
            or record["region"] != "left-half"
            or record["sha256"] != PDF_SHA
            or record["page_image_sha256"] != PAGE_SHA
        ):
            raise ValueError("paginated document differs from the supported typeset PDF and page")
        if (
            item["kind"] != "born-digital"
            or item.get("sha256") != record["sha256"]
            or item["id"] != record["digital_item"]
            or item.get("record_url") != URL
            or use.get("evidence_sha256") != record["page_image_sha256"]
            or use.get("address", {}).get("text") != "ordinarium.aufer-a-nobis"
            or use.get("role") != "corroborating_latin_witness"
            or not isinstance(use.get("locator", {}).get("section"), str)
            or not use["locator"]["section"].strip()
        ):
            raise ValueError("paginated document source-use/item identity differs")
        resolved[record["use"]] = deepcopy(record)
    return {"contract": "paginated-document-inventory-1", "documents": resolved}
