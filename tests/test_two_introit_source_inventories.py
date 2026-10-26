"""Two proper-page Introits expand actual Gloria and antiphon-repeat cues."""

import json
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from build_reader.bibliography_bindings import (
    BindingError,
    collation_subject,
    digest,
    witness_subject,
)
from checks.raw_binding import BindingError as RawBindingError

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = "witnesses/raw/bindings.json"
REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
COMMON_IMAGE = "215182ac2415d178917c183486c716ce352777a6084da024e7293a95649b60c7"
GLORIA = (
    "Glória Patri, et Fílio, et Spirítui Sancto. Sicut erat in princípio, "
    "et nunc, et semper, et in sǽcula sæculórum. Amen."
)
CASES = {
    "corpus": ("corporis-christi-introitus", "corpus-christi-introit", 57, 15, 22),
    "heart": ("sacratissimi-cordis-iesu-introitus", "sacred-heart-introit", 63, 18, 25),
}
RAW_DIGESTS = {
    "do-tempora-pent01-4": ("b8953975a5875a8506f2476fb2ea144a896d86b1736855e39fe45a7ae1e00220"),
    "sacred-heart-day": ("91ec8c8bad8090b84ac63ba2cf77d2b3a24f94dd85b2e48440bd0ad66b25082c"),
    "prayers": ("7bf86beb01c170212fa07438de45b16b321f117013321400d65c2229c6624d9b"),
}
PROPER = {
    "corpus": (369, 450, ("e1d19ee2fe941b449382c07f7f2068bbb87f64a60440e7643a650a08b51b63bb")),
    "heart": (373, 454, ("8629ac8be52969c32d528fa31e2a1794fd51c998e06b0bae4aae1733be4c9877")),
}


@pytest.fixture(scope="module")
def source_graph():
    return json.loads((ROOT / "bibliography/graph.json").read_text(encoding="utf-8"))


def record(graph, collection, identity):
    rows = [row for row in graph[collection] if row["id"] == identity]
    assert len(rows) == 1
    return rows[0]


def identities(case, kind):
    slug, key, *_ = CASES[case]
    text = "proprium." + slug
    suffix = "mr1962" if kind == "mr" else "do44667ff"
    return text, f"witness.{text}.{suffix}", f"use.{text}.{suffix}", key


def document(case):
    return json.loads(
        (ROOT / "texts/proprium" / (CASES[case][0] + ".json")).read_text(encoding="utf-8")
    )


def surface(segment):
    return " ".join(
        word.get("pre", "") + word["form"] + word.get("post", "")
        for word in segment.get("words", [])
    )


def review_matches(review, subject):
    if review["status"] == "reviewed":
        assert review == {"status": "reviewed", "sha256": digest(subject)}
    else:
        assert review == {"status": "pending"}


@pytest.mark.parametrize("case", ["corpus", "heart"])
def test_literal_proper_and_declared_common_expansions(source_graph, case):
    graph, doc = source_graph, document(case)
    text, mr_id, primary_id, key = identities(case, "mr")
    _, _, size, antiphon, proper = CASES[case]
    segments = doc["segments"]
    assert [s["id"] for s in segments] == ["s01", "s02", "s03", "s04", "s05"]
    assert [len(s.get("words", [])) for s in segments] == [
        antiphon,
        proper - antiphon,
        20,
        0,
        antiphon,
    ]
    words = [word for segment in segments for word in segment.get("words", [])]
    assert [word["id"] for word in words] == [f"w{i:03}" for i in range(1, size + 1)]
    assert segments[3]["type"] == "rubric"
    assert surface(segments[2]) == GLORIA
    assert surface(segments[0]) == surface(segments[4])
    mr = record(graph, "witnesses", mr_id)
    assert mr["orthography_profile"] == "page-body-with-declared-house-expansion"
    supplements = sorted(
        f"use.{text}.{name}" for name in ["expanded-doxology.mr1962", "introit-expansion.mr1962"]
    )
    assert mr["source_dependencies"] == {"uses": supplements, "raw_binding": None}
    primary = record(graph, "uses", primary_id)
    page, leaf, image = PROPER[case]
    assert primary["evidence_sha256"] == image
    assert primary["locator"] == {
        "printed": f"p. {page}",
        "scan": f"leaf n{leaf} / PDF p. {leaf + 1}",
        "page_url": f"https://archive.org/details/missale-romanum-1962/page/n{leaf}/mode/1up",
    }
    assert "abbreviated" in primary["claim"]
    assert "does not print" in primary["claim"]
    for use_id in supplements:
        use = record(graph, "uses", use_id)
        assert use["locator"]["printed"] == "p. 1"
        assert use["evidence_sha256"] == COMMON_IMAGE
        assert use["address"]["text"] == text
        assert use["edition"] == primary["edition"]
    formula = record(graph, "uses", f"use.{text}.expanded-doxology.mr1962")
    repeat = record(graph, "uses", f"use.{text}.introit-expansion.mr1962")
    assert formula["address"] == {"kind": "segment", "text": text, "segment": "s03"}
    assert formula["role"] == "official_text"
    assert repeat["role"] == "rubric_control" and "throughout the year" in repeat["claim"]
    for kind in ["mr", "do"]:
        _, witness_id, _, _ = identities(case, kind)
        witness = record(graph, "witnesses", witness_id)
        subject = witness_subject(ROOT, witness, graph, doc)
        expected_uses = {witness["use"], *witness["source_dependencies"]["uses"]}
        assert set(subject["source_uses"]) == expected_uses
        review_matches(witness["review"], subject)
        transcript = (ROOT / "witnesses" / text / (kind + ".txt")).read_text(encoding="utf-8")
        assert "../private/" not in transcript and "# local-archive:" not in transcript
        body = [line for line in transcript.splitlines() if line and not line.startswith("#")]
        if kind == "mr":
            assert body == [surface(s) for s in segments if s.get("words")]
        else:
            assert witness["source_dependencies"] == {
                "uses": [f"use.{text}.gloria-macro.do44667ff"],
                "raw_binding": key,
            }
            resolution = subject["raw_resolution"]
            assert resolution["binding_id"] == key
            assert resolution["binding"]["revision"] == REVISION
            assert resolution["contract"] == (
                "raw-reading-1" if case == "corpus" else "raw-reading-2"
            )
            proper_archive = "do-tempora-pent01-4" if case == "corpus" else "sacred-heart-day"
            assert set(resolution["archives"]) == {"prayers", proper_archive}
            for archive in resolution["archives"]:
                assert resolution["archives"][archive]["sha256"] == RAW_DIGESTS[archive]
            assert (
                subject["source_uses"][witness["use"]]["use"]["evidence_sha256"]
                == (RAW_DIGESTS[proper_archive])
            )
            assert (
                subject["source_uses"][f"use.{text}.gloria-macro.do44667ff"]["use"][
                    "evidence_sha256"
                ]
                == RAW_DIGESTS["prayers"]
            )


@pytest.mark.parametrize("case", ["corpus", "heart"])
@pytest.mark.parametrize("kind", ["mr", "do"])
@pytest.mark.parametrize("damage", ["inventory", "foreign-source", "transcript"])
def test_source_api_rejects_damage_and_same_copy_recovers(source_graph, case, kind, damage):
    bad = deepcopy(source_graph)
    doc = document(case)
    _, witness_id, use_id, _ = identities(case, kind)
    witness = record(bad, "witnesses", witness_id)
    target = record(bad, "uses", use_id) if damage == "foreign-source" else witness
    saved = deepcopy(target)
    if damage == "inventory":
        del target["source_dependencies"]
    elif damage == "foreign-source":
        target["address"] = {"kind": "text", "text": "proprium.foreign-source"}
    else:
        target["transcription_sha256"] = "0" * 64
    assert target != saved
    try:
        with pytest.raises(BindingError):
            witness_subject(ROOT, witness, bad, doc)
    finally:
        target.clear()
        target.update(saved)
    assert bad == source_graph
    assert witness_subject(ROOT, witness, bad, doc) == witness_subject(
        ROOT, record(source_graph, "witnesses", witness_id), source_graph, doc
    )


def isolated_digital_root(tmp_path, case):
    registry = json.loads((ROOT / REGISTRY).read_bytes())
    text, _, _, key = identities(case, "do")
    binding = registry["bindings"][key]
    assert binding["witness"] == f"witnesses/{text}/do.txt"
    archives = {
        span["archive"]
        for field in ("evidence", "references", "reading")
        for span in binding[field]
    }
    registry = {
        **registry,
        "archives": {name: row for name, row in registry["archives"].items() if name in archives},
        "bindings": {key: binding},
    }
    assert set(registry["archives"]) == archives
    registry_raw = (json.dumps(registry, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    paths = [binding["witness"]]
    paths += [row["path"] for row in registry["archives"].values()]
    for relative in paths:
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, destination)
    registry_path = tmp_path / REGISTRY
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_bytes(registry_raw)
    return registry, registry_raw


@pytest.mark.parametrize("case", ["corpus", "heart"])
@pytest.mark.parametrize("damage", ["reference", "omit", "duplicate", "wrong-evidence"])
def test_digital_chain_rejects_damage_and_same_copy_recovers(source_graph, tmp_path, case, damage):
    registry, registry_raw = isolated_digital_root(tmp_path, case)
    graph = deepcopy(source_graph)
    _, witness_id, use_id, key = identities(case, "do")
    witness = record(graph, "witnesses", witness_id)
    doc = document(case)
    healthy = witness_subject(tmp_path, witness, graph, doc)
    saved_graph, saved_registry = deepcopy(graph), deepcopy(registry)
    plan = registry["bindings"][key]
    if damage == "reference":
        plan["references"][0]["target"] = 0
    elif damage == "omit":
        del plan["reading"][2]
    elif damage == "duplicate":
        plan["reading"].append(deepcopy(plan["reading"][0]))
    else:
        record(graph, "uses", use_id)["evidence_sha256"] = (
            "2701acd15dc559283b10e5f1d7f6831ce9b5db34938dbae319cdc48d95e70e6d"
        )
    assert registry != saved_registry or graph != saved_graph
    try:
        (tmp_path / REGISTRY).write_text(json.dumps(registry), encoding="utf-8")
        with pytest.raises((BindingError, RawBindingError)):
            witness_subject(tmp_path, witness, graph, doc)
    finally:
        graph.clear()
        graph.update(saved_graph)
        (tmp_path / REGISTRY).write_bytes(registry_raw)
    assert witness_subject(tmp_path, record(graph, "witnesses", witness_id), graph, doc) == healthy


def test_paschal_tail_cannot_be_silently_included(source_graph, tmp_path):
    registry, raw = isolated_digital_root(tmp_path, "heart")
    _, witness_id, _, key = identities("heart", "do")
    witness = record(source_graph, "witnesses", witness_id)
    doc = document("heart")
    healthy = witness_subject(tmp_path, witness, source_graph, doc)
    saved = deepcopy(registry)
    plan = registry["bindings"][key]
    full = (
        (ROOT / registry["archives"]["sacred-heart-day"]["path"])
        .read_text(encoding="utf-8")
        .splitlines()[17]
    )
    assert full.endswith(" (Allelúja, allelúja.)")
    plan["evidence"][1]["fragment"]["end"] = len(full)
    plan["evidence"][1]["fragment"]["text"] = full
    plan["reading"][0]["fragment"]["end"] = len(full)
    assert registry != saved
    try:
        (tmp_path / REGISTRY).write_text(json.dumps(registry), encoding="utf-8")
        with pytest.raises((BindingError, RawBindingError)):
            witness_subject(tmp_path, witness, source_graph, doc)
    finally:
        (tmp_path / REGISTRY).write_bytes(raw)
    assert witness_subject(tmp_path, witness, source_graph, doc) == healthy


@pytest.mark.parametrize("case", ["corpus", "heart"])
def test_collation_stays_bound_to_the_unchanged_selected_body(source_graph, case):
    doc = document(case)
    text = doc["id"]
    collation = record(source_graph, "collations", f"collation.{text}.mr1962-do44667ff")
    witnesses = {
        identity: witness_subject(
            ROOT, record(source_graph, "witnesses", identity), source_graph, doc
        )
        for identity in collation["witnesses"]
    }
    for identity, subject in witnesses.items():
        review_matches(record(source_graph, "witnesses", identity)["review"], subject)
    if collation["review"]["status"] == "reviewed":
        assert all(
            record(source_graph, "witnesses", identity)["review"]["status"] == "reviewed"
            for identity in witnesses
        )
    healthy = collation_subject(ROOT, collation, doc, witnesses)
    review_matches(collation["review"], healthy)
    bad = deepcopy(doc)
    saved = deepcopy(bad["segments"][0]["words"][0])
    bad["segments"][0]["words"][0]["post"] = "!"
    assert bad != doc
    try:
        with pytest.raises(BindingError):
            collation_subject(ROOT, collation, bad, witnesses)
    finally:
        bad["segments"][0]["words"][0].clear()
        bad["segments"][0]["words"][0].update(saved)
    assert bad == doc and collation_subject(ROOT, collation, bad, witnesses) == healthy
