"""A prayer's final Amen and the second amen of a doubled saying are distinct."""

from pathlib import Path

from build_reader import store

ROOT = Path(__file__).resolve().parents[1]


def test_english_amen_captions_follow_the_response_or_saying():
    closing = set()
    first = set()
    second = set()
    for path in (ROOT / "texts").glob("*/*.json"):
        text = f"{path.parent.name}.{path.stem}"
        body = store.core(ROOT, text)
        layer = store.raw_layer(ROOT, "en", text)
        for verse in body["segments"]:
            words = verse.get("words", [])
            translation = layer["segments"].get(verse["id"], {}).get("translation", "")
            for index, word in enumerate(words):
                if word["form"].lower() != "amen":
                    continue
                caption = layer["words"][word["id"]].get("gloss", "")
                if caption.lower() != "amen":
                    continue
                if index == len(words) - 1 and translation.endswith("Amen."):
                    assert caption == "Amen", (text, word["id"])
                    closing.add(text)
                elif index + 1 < len(words) and word["form"] == "Amen" and "Amen" in translation:
                    assert caption == "Amen", (text, word["id"])
                    first.add(text)
                elif index and words[index - 1]["form"] == "Amen" and "Amen, amen" in translation:
                    assert caption == "amen", (text, word["id"])
                    second.add(text)
    assert {"orationes.adoro-te-devote", "orationes.pater-noster"} <= closing
    assert "proprium.dominica-i-adventus-evangelium" in first
    assert "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-evangelium" in first & second
