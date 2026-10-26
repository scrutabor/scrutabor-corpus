"""Explicit document contracts; unrelated PDF subjects retain their exact shape."""

from . import compendium_html, paginated_documents


def _is_compendium(value):
    return isinstance(value, list) and any(
        isinstance(record, dict) and record.get("contract") == compendium_html.CONTRACT
        for record in value
    )


def declarations(value):
    if _is_compendium(value):
        return compendium_html.declarations(value)
    return paginated_documents.declarations(value)


def requires_compendium(witness):
    """Only the seven named assertions require this exact explicit profile."""
    return isinstance(witness, dict) and witness.get("id") in {
        scope["witness"] for scope in compendium_html.SCOPES.values()
    }


def resolve_documents(value, sources, *, witness=None, doc=None, transcript=None):
    if _is_compendium(value) or requires_compendium(witness):
        return compendium_html.resolve_documents(
            value, sources, witness=witness, doc=doc, transcript=transcript
        )
    return paginated_documents.resolve_documents(value, sources)
