"""A text's source method that says its Divinum Officium reading is bound to its raw archives is
true only where that binding exists: an entry in the raw binding register for the text's `do`
witness, or retained raw files named by that witness's own path lines. A reading whose binding is
pending says so instead.
"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAIM = "bound to its raw archive"


def claiming_texts():
    for path in sorted((ROOT / "texts").glob("*/*.json")):
        doc = json.loads(path.read_text(encoding="utf-8"))
        method = ((doc.get("editorial") or {}).get("source") or {}).get("method", "")
        if CLAIM in method:
            yield f"{path.parent.name}.{path.stem}"


def retained(relative):
    path = ROOT / relative
    return path.exists() and any(
        line.startswith("# path: witnesses/raw/")
        for line in path.read_text(encoding="utf-8").splitlines()
    )


def test_every_raw_binding_claim_has_its_binding():
    register = json.loads((ROOT / "witnesses/raw/bindings.json").read_text(encoding="utf-8"))
    bound = {entry["witness"] for entry in register["bindings"].values()}
    texts = list(claiming_texts())
    assert len(texts) > 100
    unbound = [
        text
        for text in texts
        if f"witnesses/{text}/do.txt" not in bound and not retained(f"witnesses/{text}/do.txt")
    ]
    assert unbound == []
