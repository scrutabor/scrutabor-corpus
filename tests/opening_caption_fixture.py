"""Reverse eight exact reviewed opening captions before older whole-object inverses."""

from copy import deepcopy

OPENINGS = {
    "orationes.memorare": ("be mindful", "Be mindful"),
    "ordinarium.praefatio-apostolorum": ("truly", "Truly"),
    "ordinarium.praefatio-d-n-iesu-christi-regis": ("truly", "Truly"),
    "ordinarium.praefatio-defunctorum": ("truly", "Truly"),
    "ordinarium.praefatio-epiphaniae": ("truly", "Truly"),
    "ordinarium.praefatio-nativitatis": ("truly", "Truly"),
    "proprium.cathedra-sancti-petri-secreta": ("of Church", "Of Church"),
    "proprium.commemoratio-omnium-fidelium-defunctorum-missa-i-sequentia": ("day", "Day"),
}


def restore_opening_layer(layer):
    """Keep every other field and reject stale or unreviewed opening values."""
    result = deepcopy(layer)
    change = OPENINGS.get(result["text"])
    if change is None:
        return result
    before, after = change
    assert result["language"] == "en", "reviewed opening language"
    assert result["words"]["w001"].get("gloss") == after, "reviewed opening caption"
    result["words"]["w001"]["gloss"] = before
    return result
