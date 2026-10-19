"""Explicit D framing and Mass performer scope in the pinned Palm source."""

import copy
import hashlib
import json
from pathlib import Path

import pytest
from test_attribution_scope import marker_source

from checks import attribute
from checks.raw_binding import REGISTRY, BindingError, resolve_binding

ROOT = Path(__file__).resolve().parent.parent
KEY = "palm-ministers"
ARCHIVE = "do-tempora-quad6-0r"
TEXT_ID = "ordinarium.test"
BODIES = (
    "Jube, domne, benedícere.",
    "Dóminus sit in córdibus vestris et in lábiis vestris: ut digne et competénter "
    "annuntiétis Evangélium suum: In nómine Patris, et Fílii, + et Spíritus Sancti.",
    "Amen.",
)


def save(root, data):
    (root / REGISTRY).write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def palm(tmp_path, monkeypatch):
    original = json.loads((ROOT / REGISTRY).read_text(encoding="utf-8"))
    archive = copy.deepcopy(original["archives"][ARCHIVE])
    raw = (ROOT / archive["path"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == archive["sha256"]
    assert archive["revision"] == "44667ff518b8ff1439780470828b39714f5306a2"
    assert archive["upstream"] == "web/www/missa/Latin/Tempora/Quad6-0r.txt"
    lines = raw.decode("utf-8").splitlines()
    assert lines[239] == "[Munda Cor Passionis]"
    assert lines[240].startswith("Munda cor meum ac lábia mea,")
    assert lines[241:244] == ["D. " + BODIES[0], "S. " + BODIES[1], "D. " + BODIES[2]]
    binding = {
        "witness": "witnesses/ordinarium.test/do.txt",
        "revision": archive["revision"],
        "evidence": [
            {
                "archive": ARCHIVE,
                "first": 242,
                "last": 244,
                "section": "Munda Cor Passionis",
                "section_line": 240,
            }
        ],
        "references": [],
        "reading": [{"archive": ARCHIVE, "first": 242, "last": 244}],
    }
    data = {"version": 1, "archives": {ARCHIVE: archive}, "bindings": {KEY: binding}}
    target = tmp_path / archive["path"]
    target.parent.mkdir(parents=True)
    target.write_bytes(raw)
    save(tmp_path, data)
    witness = tmp_path / binding["witness"]
    witness.parent.mkdir(parents=True)
    witness.write_text(
        "# witness: do\n# revision: "
        + archive["revision"]
        + "\n# raw-binding: "
        + KEY
        + "\n# path: "
        + archive["upstream"]
        + " [Munda Cor Passionis] (lines 242-244)\n"
        + "\n".join(BODIES)
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(attribute, "CORPUS", tmp_path)
    return tmp_path, witness, data


def document():
    return {
        "id": TEXT_ID,
        "category": "ordinarium",
        "segments": [
            {
                "id": f"s{i:02d}",
                "type": "verse",
                "words": [
                    {"id": f"w{i:02d}-{j:02d}", "form": form}
                    for j, form in enumerate(body.split(), 1)
                    if form != "+"
                ],
            }
            for i, body in enumerate(BODIES, 1)
        ],
    }


def test_complete_palm_reading_keeps_action_sign_and_excludes_munda(palm):
    root, witness, _ = palm
    bound = resolve_binding(witness, root)
    assert bound.text == " ".join(BODIES)
    assert bound.source["contract"] == "raw-reading-1"
    assert [f.line for f in bound.fragments] == [242, 243, 244]
    assert [f.marker for f in bound.fragments] == ["D", "S", "D"]
    assert [f.text for f in bound.fragments] == list(BODIES)
    assert [f.raw for f in bound.fragments] == [
        "D. " + BODIES[0],
        "S. " + BODIES[1],
        "D. " + BODIES[2],
    ]
    assert bound.text.count("+") == 1
    assert len([word for word in bound.text.split() if word != "+"]) == 28
    assert "Munda cor meum" not in bound.text
    assert attribute.span_covers(document())


@pytest.mark.parametrize("mass", [True, False])
def test_actual_palm_markers_name_actors_only_inside_mass(palm, mass):
    _, _, _ = palm
    expected = (
        list(
            zip(
                ["minister", "sacerdos", "minister"],
                [attribute.flatten(body) for body in BODIES],
                strict=True,
            )
        )
        if mass
        else []
    )
    assert attribute.marked_lines(TEXT_ID, mass=mass) == expected
    if mass:
        result = attribute.propose(document())
        assert [result[f"s{i:02d}"]["speaker"] for i in range(1, 4)] == [
            "minister",
            "sacerdos",
            "minister",
        ]


@pytest.mark.parametrize(
    "change",
    [
        "drop-plus",
        "drop-request",
        "drop-amen",
        "repeat-amen",
        "munda",
        "wrong-section",
        "revision",
        "archive-bytes",
    ],
)
def test_exact_source_guards_reject_and_restore(palm, change):
    root, witness, data = palm
    original = witness.read_bytes()
    original_data = copy.deepcopy(data)
    raw = root / data["archives"][ARCHIVE]["path"]
    original_raw = raw.read_bytes()
    assert resolve_binding(witness, root)
    if change in {"drop-plus", "drop-request", "drop-amen", "repeat-amen"}:
        body = witness.read_text(encoding="utf-8")
        body = {
            "drop-plus": body.replace(", + et", ", et"),
            "drop-request": body.replace(BODIES[0] + "\n", ""),
            "drop-amen": body.removesuffix("Amen.\n"),
            "repeat-amen": body + "Amen.\n",
        }[change]
        witness.write_text(body, encoding="utf-8")
    elif change == "munda":
        data["bindings"][KEY]["reading"][0]["first"] = 241
    elif change == "wrong-section":
        data["bindings"][KEY]["evidence"][0]["section_line"] = 236
    elif change == "revision":
        data["bindings"][KEY]["revision"] = "0" * 40
    else:
        raw.write_bytes(original_raw + b"\n")
    save(root, data)
    with pytest.raises(BindingError):
        resolve_binding(witness, root)
    assert attribute.marked_lines(TEXT_ID) == []
    assert not attribute.span_covers(document())
    witness.write_bytes(original)
    raw.write_bytes(original_raw)
    save(root, original_data)
    assert resolve_binding(witness, root).text == " ".join(BODIES)
    assert attribute.span_covers(document())


@pytest.mark.parametrize("explicit", [True, False])
@pytest.mark.parametrize("mass", [True, False])
def test_legacy_d_marker_uses_existing_scope_and_textual_routes(
    tmp_path, monkeypatch, explicit, mass
):
    raw = tmp_path / "source.txt"
    raw.write_text("D. Jube, domne, benedícere.\n", encoding="utf-8")
    marker_source(tmp_path, monkeypatch, raw, TEXT_ID)
    monkeypatch.setattr(attribute, "_source_ranges", lambda _: [(raw, 1, 1, explicit)])
    expected = [("minister", attribute.flatten(BODIES[0]))] if mass else []
    assert attribute.marked_lines(TEXT_ID, mass=mass) == expected
    doc = document()
    doc["segments"] = doc["segments"][:1]
    assert attribute.span_covers(doc)


@pytest.mark.parametrize("marker", ["s", "m", "v", "r", "o", "d"])
@pytest.mark.parametrize("mass", [True, False])
def test_lowercase_prefixes_do_not_acquire_actor_semantics(tmp_path, monkeypatch, marker, mass):
    raw = tmp_path / "source.txt"
    raw.write_text(marker + ". Amen.\n", encoding="utf-8")
    marker_source(tmp_path, monkeypatch, raw, TEXT_ID)
    monkeypatch.setattr(attribute, "_source_ranges", lambda _: [(raw, 1, 1, False)])
    assert attribute.marked_lines(TEXT_ID, mass=mass) == []


def test_lowercase_d_remains_literal_not_new_textual_framing(palm):
    root, witness, data = palm
    raw = root / data["archives"][ARCHIVE]["path"]
    source = raw.read_text(encoding="utf-8").replace("D. ", "d. ")
    raw.write_text(source, encoding="utf-8")
    data["archives"][ARCHIVE]["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    save(root, data)
    with pytest.raises(BindingError):
        resolve_binding(witness, root)
    witness.write_text(
        witness.read_text(encoding="utf-8")
        .replace("\nJube,", "\nd. Jube,")
        .replace("\nAmen.\n", "\nd. Amen.\n"),
        encoding="utf-8",
    )
    bound = resolve_binding(witness, root)
    assert [f.marker for f in bound.fragments] == [None, "S", None]
    assert bound.fragments[0].text == "d. " + BODIES[0]
    assert bound.fragments[2].text == "d. Amen."


def test_partial_d_request_keeps_verified_physical_actor_context(palm):
    root, witness, data = palm
    binding = data["bindings"][KEY]
    binding["contract"] = "raw-reading-2"
    end = len("D. " + BODIES[0])
    binding["evidence"][0].update(
        last=242,
        fragment={
            "start": 3,
            "end": end,
            "text": BODIES[0],
            "marker": "D",
            "reason": "Complete request after its explicit physical-line D prefix.",
        },
    )
    binding["reading"][0].update(last=242, fragment={"start": 3, "end": end})
    text = witness.read_text(encoding="utf-8")
    header = text.split("\n" + BODIES[0], 1)[0]
    header = header.replace("lines 242-244", f"line 242, chars 3:{end}")
    witness.write_text(header + "\n" + BODIES[0] + "\n", encoding="utf-8")
    save(root, data)
    bound = resolve_binding(witness, root)
    assert bound.text == BODIES[0]
    assert bound.fragments[0].marker == "D"
    assert bound.fragments[0].marker_scope_verified
    assert attribute.marked_lines(TEXT_ID) == [("minister", attribute.flatten(BODIES[0]))]
    assert attribute.marked_lines(TEXT_ID, mass=False) == []


def test_partial_contract_rejects_ambiguous_inline_d_marker(palm):
    root, witness, data = palm
    data["bindings"][KEY]["contract"] = "raw-reading-2"
    raw = root / data["archives"][ARCHIVE]["path"]
    raw.write_text(
        raw.read_text(encoding="utf-8").replace("S. " + BODIES[1], "S. " + BODIES[1] + " D. Amen."),
        encoding="utf-8",
    )
    data["archives"][ARCHIVE]["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    witness.write_text(
        witness.read_text(encoding="utf-8").replace(BODIES[1], BODIES[1] + " D. Amen."),
        encoding="utf-8",
    )
    save(root, data)
    with pytest.raises(BindingError, match="ambiguous inline source marker"):
        resolve_binding(witness, root)
    assert attribute.marked_lines(TEXT_ID) == []
    assert not attribute.span_covers(document())


def test_terminal_framing_does_not_remove_d_actor_or_plus(palm):
    root, witness, data = palm
    binding = data["bindings"][KEY]
    binding["contract"] = "raw-reading-3"
    raw = root / data["archives"][ARCHIVE]["path"]
    raw.write_text(
        raw.read_text(encoding="utf-8").replace("D. Amen.\n", "D. Amen.~\n"), encoding="utf-8"
    )
    data["archives"][ARCHIVE]["sha256"] = hashlib.sha256(raw.read_bytes()).hexdigest()
    binding["framing"] = [
        {
            "archive": ARCHIVE,
            "line": 244,
            "start": 8,
            "end": 9,
            "text": "~",
            "kind": "terminal-continuation-tilde",
            "reason": "Explicit test-created control.",
        }
    ]
    save(root, data)
    bound = resolve_binding(witness, root)
    assert bound.text == " ".join(BODIES)
    assert bound.fragments[-1].marker == "D"
    assert bound.fragments[-1].raw == "D. Amen.~"
    assert bound.fragments[-1].framing[0].text == "~"
    assert bound.text.count("+") == 1
    assert attribute.marked_lines(TEXT_ID)[-1] == ("minister", attribute.flatten("Amen."))


def test_contiguous_raw_parts_keep_one_performer_occurrence(palm):
    root, witness, data = palm
    data["bindings"][KEY]["reading"] = [
        {"archive": ARCHIVE, "first": 242, "last": 243},
        {"archive": ARCHIVE, "first": 244, "last": 244},
    ]
    save(root, data)
    bound = resolve_binding(witness, root)
    assert bound.text == " ".join(BODIES)
    raw = root / data["archives"][ARCHIVE]["path"]
    assert bound.spans == ((raw, 242, 243), (raw, 244, 244))
    result = attribute.assess(document())
    assert result.scope == "SCOPED" and result.write_eligible
    assert [result.proposals[f"s{i:02d}"]["speaker"] for i in range(1, 4)] == [
        "minister",
        "sacerdos",
        "minister",
    ]


def test_reordered_raw_parts_remain_textual_not_performer_evidence(palm):
    root, witness, data = palm
    data["bindings"][KEY]["reading"] = [
        {"archive": ARCHIVE, "first": 244, "last": 244},
        {"archive": ARCHIVE, "first": 242, "last": 243},
    ]
    text = witness.read_text(encoding="utf-8")
    header = "\n".join(line for line in text.splitlines() if line.startswith("#"))
    witness.write_text(header + "\n" + "\n".join((BODIES[2], *BODIES[:2])) + "\n", encoding="utf-8")
    save(root, data)
    bound = resolve_binding(witness, root)
    assert bound.text == " ".join((BODIES[2], *BODIES[:2]))
    doc = document()
    doc["segments"] = [doc["segments"][2], *doc["segments"][:2]]
    result = attribute.assess(doc)
    assert result.scope == "COMPOSITE_TEXT_ONLY" and result.proposals == {}
    assert not result.write_eligible
    assert attribute.marked_lines(TEXT_ID) == []
