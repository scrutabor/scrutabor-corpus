"""Complete bibliographic source records for native documentary expectations."""

from edition_revision_fixture import current_bibliography_record

COLLECTIONS = {
    "use": "uses",
    "work": "works",
    "edition": "editions",
    "digital_item": "digital_items",
}


def current_source_uses(groups):
    return {
        identity: {
            part: current_bibliography_record(COLLECTIONS[part], row)
            for part, row in records.items()
        }
        for identity, records in groups.items()
    }
