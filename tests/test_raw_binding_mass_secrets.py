"""Literal Mass/Common Secret chains, exact context, and text-only boundaries."""

import copy
import hashlib
import json
import re
import shutil
from contextlib import contextmanager
from pathlib import Path

import pytest

from build_reader.bibliography import public_text_evidence
from build_reader.bibliography_bindings import (
    collation_subject,
    transcript_digest,
    validate_bindings,
    witness_subject,
)
from checks import attribute, raw_binding, raw_binding_mass_secrets, transcription

ROOT = Path(__file__).resolve().parents[1]
REVISION = "44667ff518b8ff1439780470828b39714f5306a2"
PROFILE = "roman1960-latin-missa-two-inherited-secrets"
FORMULA = (
    "Per Dóminum nostrum Jesum Christum, Fílium tuum: qui tecum vivit et regnat "
    "in unitáte Spíritus Sancti Deus, per ómnia sǽcula sæculórum. Amen."
)
CASES = {
    "maternity": {
        "text": "proprium.maternitas-beatae-mariae-virginis-secreta",
        "key": "secret-maternitas-do44667ff",
        "sections": [
            ("do-sancti-10-11", 46, 47, "@Commune/C10"),
            ("common-c10", 216, 217, "@Commune/C11"),
            ("common-c11", 400, 402, "$Per Dominum"),
        ],
        "literal": (
            "Tua, Dómine, propitiatióne, et beátæ Maríæ semper Vírginis intercessióne, "
            "ad perpétuam atque præséntem hæc oblátio nobis profíciat prosperitátem "
            "et pacem. " + FORMULA
        ),
        "selected_words": 46,
        "literal_words": 42,
        "old_DO_sha256": "a18dcac55e2e84e6cf568bb5522eb1bceb0602a21ad2346a0acc1454dc38cc5e",
    },
    "all-saints": {
        "text": "proprium.omnium-sanctorum-secreta",
        "key": "secret-omnium-sanctorum-do44667ff",
        "sections": [
            ("all-saints", 41, 42, "@Commune/C3a"),
            ("common-c3a", 62, 64, "$Per Dominum"),
        ],
        "literal": (
            "Múnera tibi, Dómine, nostra devotiónis offérimus: quæ et pro tuórum "
            "tibi grata sint honóre Justórum, et nobis salutária, te miseránte, "
            "reddántur. " + FORMULA
        ),
        "selected_words": 43,
        "literal_words": 43,
        "old_DO_sha256": "ca4375e5cbd2210ef96082de1ff498865c2eb28ceeb3a7b23fcaa9ad3c5fb5fc",
    },
}
ARCHIVES = {
    "do-sancti-10-11": (
        "web/www/missa/Latin/Sancti/10-11.txt",
        "606473b4f90e617b60963fb74ed42e82055c7f73f56fdbba969f6753a8f24b16",
    ),
    "all-saints": (
        "web/www/missa/Latin/Sancti/11-01.txt",
        "b6e49964e28e5a136b4733ef923255e1c2a279e9818a21247e8315abc58e4112",
    ),
    "common-c10": (
        "web/www/horas/Latin/Commune/C10.txt",
        "463fcb39e6d91e899a4da4c608ecb0d45d51f1d983769efceaad975a69ab108e",
    ),
    "common-c11": (
        "web/www/horas/Latin/Commune/C11.txt",
        "cff3086e9c0f698b67c7fa0972d2b8cd7a953b4fe45fbf23100ec471db27c428",
    ),
    "common-c3a": (
        "web/www/horas/Latin/Commune/C3a.txt",
        "023a499c135df597cd53da1232d042a2f3b603b432da704ad2c2739f56567312",
    ),
    "prayers": (
        "web/www/missa/Latin/Ordo/Prayers.txt",
        "7bf86beb01c170212fa07438de45b16b321f117013321400d65c2229c6624d9b",
    ),
    "missa-ordo-44667ff": (
        "web/www/missa/Latin/Ordo/Ordo.txt",
        "a7f63e8030325b809f74dd4587c649bf8eb45cdd150fc9a2817fe2a1ed6a42e3",
    ),
}
PINNED_OBJECT = "raw-reading-9 requires the exact pinned source objects"


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def files(root):
    return {p.relative_to(root): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def one(rows, identity):
    (row,) = [row for row in rows if row["id"] == identity]
    return row


@pytest.fixture
def source(request, tmp_path):
    case = copy.deepcopy(CASES[request.param])
    root = tmp_path / "corpus"
    tid, key = case["text"], case["key"]
    full_registry = json.loads((ROOT / raw_binding.REGISTRY).read_text())
    binding = copy.deepcopy(full_registry["bindings"][key])
    assert binding == {
        "witness": f"witnesses/{tid}/do.txt",
        "revision": REVISION,
        "contract": "raw-reading-9",
        "profile": PROFILE,
    }
    keys = [s[0] for s in case["sections"]] + ["prayers", "missa-ordo-44667ff"]
    registry = {
        "version": full_registry["version"],
        "archives": {k: copy.deepcopy(full_registry["archives"][k]) for k in keys},
        "bindings": {key: binding},
    }
    inputs = {raw_binding.REGISTRY, "bibliography/graph.json"}
    for k, record in registry["archives"].items():
        raw = (ROOT / record["path"]).read_bytes()
        assert (record["upstream"], hashlib.sha256(raw).hexdigest()) == ARCHIVES[k]
        target = root / record["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        inputs.add(record["path"])
    folder = Path("witnesses") / tid
    shutil.copytree(ROOT / folder, root / folder)
    inputs.update(p.relative_to(ROOT).as_posix() for p in (ROOT / folder).rglob("*") if p.is_file())
    core = "texts/" + tid.replace(".", "/", 1) + ".json"
    target = root / core
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((ROOT / core).read_bytes())
    inputs.add(core)
    put(root / raw_binding.REGISTRY, registry)
    graph = json.loads((ROOT / "bibliography/graph.json").read_text())
    graph["witnesses"] = [w for w in graph["witnesses"] if w["text"] == tid]
    graph["collations"] = [c for c in graph["collations"] if c["text"] == tid]
    graph["uses"] = [u for u in graph["uses"] if u["address"].get("text") == tid]
    return {
        **case,
        "case": request.param,
        "root": root,
        "registry": registry,
        "graph": graph,
        "doc": json.loads(target.read_text()),
        "witness": root / binding["witness"],
        "originals": {name: (ROOT / name).read_bytes() for name in sorted(inputs)},
    }


def witness(source, label="do44667ff"):
    return one(source["graph"]["witnesses"], f"witness.{source['text']}.{label}")


def use(source, context=False):
    suffix = "oration-boundaries.do44667ff" if context else "do44667ff"
    return one(source["graph"]["uses"], f"use.{source['text']}.{suffix}")


def resolve(source):
    return raw_binding.resolve_binding(source["witness"], source["root"])


def subject(source):
    return witness_subject(source["root"], witness(source), source["graph"], source["doc"])


def healthy(source):
    reading = resolve(source)
    assert reading is not None and reading.source["contract"] == "raw-reading-9"
    assert reading.spans == reading.fragments == ()
    assert reading.text == source["literal"]
    assert len(reading.text.split()) == source["literal_words"]
    assert reading.source["binding_id"] == source["key"]
    assert reading.source["binding"] == source["registry"]["bindings"][source["key"]]
    assert reading.source["profile"]["id"] == PROFILE
    assert reading.source["profile"]["text"] == source["text"]
    assert reading.source["profile"]["logical_caller"] == "missa"
    assert reading.source["profile"]["sections"] == [list(s) for s in source["sections"]]
    keys = [s[0] for s in source["sections"]] + ["prayers", "missa-ordo-44667ff"]
    assert {k: (v["upstream"], v["sha256"]) for k, v in reading.source["archives"].items()} == {
        k: ARCHIVES[k] for k in keys
    }
    comp = reading.source["resolved_literal_composition"]
    key, heading, _, _ = source["sections"][-1]
    assert [(p["archive"], p["line"], p["remove_prefix"]) for p in comp["pieces"]] == [
        (key, heading + 1, ""),
        ("prayers", 96, "r. "),
        ("prayers", 97, "R. "),
    ]
    assert comp["text"] == source["literal"]
    expected_context = [(k, n) for k, h, z, _ in source["sections"] for n in [h, z]]
    expected_context += [("missa-ordo-44667ff", i) for i in range(196, 203)] + [("prayers", 95)]
    assert [(c["archive"], c["line"]) for c in comp["context"]] == expected_context
    assert transcription.check_transcriptions(source["witness"].parent) == ([], 1)
    assert validate_bindings(source["root"], source["graph"]) == []
    current = subject(source)
    assert current["raw_resolution"] == reading.source
    assert set(current["source_uses"]) == {use(source)["id"], use(source, True)["id"]}
    assert witness(source)["source_dependencies"] == {
        "uses": [use(source, True)["id"]],
        "raw_binding": source["key"],
    }
    return copy.deepcopy(reading.source), current


@contextmanager
def restored(source):
    expected = healthy(source)
    before, state = files(source["root"]), copy.deepcopy(source)
    try:
        yield
    finally:
        root = state["root"]
        for p in root.rglob("*"):
            if p.is_symlink():
                p.unlink()
        for rel in set(files(root)) - set(before):
            (root / rel).unlink()
        for rel, raw in before.items():
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_bytes(raw)
        source.clear()
        source.update(state)
        assert files(root) == before
        assert healthy(source) == expected
        assert all((ROOT / name).read_bytes() == raw for name, raw in source["originals"].items())


def save_registry(source):
    put(source["root"] / raw_binding.REGISTRY, source["registry"])


def rejected_subject(source, message):
    with pytest.raises(ValueError, match=re.escape(message)):
        subject(source)
    prefix = f"bibliography witness {witness(source)['id']}: "
    assert any(
        error.startswith(prefix) and message in error
        for error in validate_bindings(source["root"], source["graph"])
    )


def rejected_raw(source, message):
    with pytest.raises(raw_binding.BindingError, match=re.escape(message)):
        resolve(source)
    errors, checked = transcription.check_transcriptions(source["witness"].parent)
    assert checked == 0 and any(message in error for error in errors)
    rejected_subject(source, message)


def rewrite(source, transform):
    old = source["witness"].read_text()
    new = transform(old)
    assert new != old
    source["witness"].write_text(new, encoding="utf-8")
    witness(source)["transcription_sha256"] = transcript_digest(new)


@pytest.mark.parametrize("source", list(CASES), indirect=True)
def test_complete_real_literal_reading_and_pending_subject(source):
    healthy(source)
    records = source["graph"]["witnesses"] + source["graph"]["collations"]
    assert all(row["review"] == {"status": "pending"} for row in records)
    subjects = {
        row["id"]: witness_subject(source["root"], row, source["graph"], source["doc"])
        for row in source["graph"]["witnesses"]
    }
    coll = one(source["graph"]["collations"], f"collation.{source['text']}.mr1962-do44667ff")
    assert (
        collation_subject(source["root"], coll, source["doc"], subjects)["contract"]
        == "collation-review-2"
    )
    app = json.loads((source["witness"].parent / "apparatus.json").read_text())
    assert len(app["adjudicated"]) == app["summary"]["entries"] == 16
    assert all(row["ruling"].strip() for row in app["adjudicated"])
    public = one(public_text_evidence(source["graph"])["texts"], source["text"])
    assert public["witnesses"] == [] and "collation" not in public
    selected = [w for s in source["doc"]["segments"] for w in s.get("words", [])]
    assert len(selected) == source["selected_words"]
    old = source["witness"].parent / "historical-2026-10-26/do.txt"
    assert hashlib.sha256(old.read_bytes()).hexdigest() == source["old_DO_sha256"]
    assert old.read_bytes() != source["witness"].read_bytes()
    mr = witness(source, "mr1962")["source_dependencies"]
    suffixes = ["oration-boundaries"]
    suffixes += (
        ["conclusion-rg115a-base", "conclusion-rg115b"]
        if source["case"] == "maternity"
        else ["conclusion-rg115a"]
    )
    assert mr == {
        "uses": sorted(f"use.{source['text']}.{s}.mr1962" for s in suffixes),
        "raw_binding": None,
    }
    forms = [w["form"] for w in selected]
    if source["case"] == "maternity":
        assert all(w in forms for w in ["Unigéniti", "tui", "Matris", "eúndem"])
    else:
        assert "nostræ" in forms and "cunctórum" in forms


@pytest.mark.parametrize("source", list(CASES), indirect=True)
def test_whitespace_only_witness_composition_remains_healthy(source):
    with restored(source):
        rewrite(
            source, lambda s: s.replace(source["literal"], "\n\t".join(source["literal"].split()))
        )
        healthy(source)


RAW_CASES = [
    ("unknown-profile", "raw-reading-9 requires a supported closed Mass Secret profile"),
    ("office-profile", "raw-reading-9 requires a supported closed Mass Secret profile"),
    ("nonstring-profile", "raw-reading-9 profile must be a string"),
    ("unsupported-contract", "unsupported per-binding contract"),
    ("extra-caller", "expected fields ['contract', 'profile', 'revision', 'witness']"),
    ("wrong-revision", "raw-reading-9 requires its exact witness and revision"),
    ("unknown-binding", "raw-reading-9 requires a supported closed Mass Secret profile"),
    ("transplanted-witness", "raw-reading-9 requires its exact witness and revision"),
    ("missing-marker", "raw-binding marker and registered witness identity disagree"),
    ("duplicate-marker", "raw-binding marker and registered witness identity disagree"),
    ("missing-binding", "raw-binding marker and registered witness identity disagree"),
    ("missa-common-alias", PINNED_OBJECT),
    ("office-conclusion", PINNED_OBJECT),
    ("missing-body-archive", "unknown archive:"),
    ("missing-ordo-archive", "unknown archive: missa-ordo-44667ff"),
    ("missing-body-file", "unreadable archive"),
    ("archive-revision", "revision differs from binding"),
    ("duplicate-archive-identity", "duplicate archive identity or local path"),
    ("duplicate-local-path", "duplicate archive identity or local path"),
    ("escape-local-path", "invalid confined path"),
    ("escaping-source-symlink", "path escapes witnesses/raw"),
]


@pytest.mark.parametrize("fault,message", RAW_CASES, ids=[r[0] for r in RAW_CASES])
@pytest.mark.parametrize("source", list(CASES), indirect=True)
def test_registry_and_context_admission_rejects_then_recovers(source, fault, message):
    with restored(source):
        binding = source["registry"]["bindings"][source["key"]]
        archives = source["registry"]["archives"]
        body = source["sections"][-1][0]
        if fault in {"unknown-profile", "office-profile"}:
            binding["profile"] = (
                "unknown" if fault == "unknown-profile" else "roman1960-latin-horas"
            )
        elif fault == "nonstring-profile":
            binding["profile"] = False
        elif fault == "unsupported-contract":
            binding["contract"] = "raw-reading-10"
        elif fault == "extra-caller":
            binding["caller"] = "missa"
        elif fault == "wrong-revision":
            binding["revision"] = "0" * 40
            rewrite(source, lambda s: s.replace(REVISION, "0" * 40))
        elif fault == "unknown-binding":
            source["registry"]["bindings"]["unrelated-secret"] = source["registry"]["bindings"].pop(
                source["key"]
            )
            rewrite(
                source,
                lambda s: s.replace(
                    "# raw-binding: " + source["key"], "# raw-binding: unrelated-secret"
                ),
            )
        elif fault == "transplanted-witness":
            other = next(c["text"] for c in CASES.values() if c["text"] != source["text"])
            binding["witness"] = f"witnesses/{other}/do.txt"
            target = source["root"] / binding["witness"]
            target.parent.mkdir(parents=True)
            target.write_bytes(source["witness"].read_bytes())
            source["witness"] = target
        elif fault == "missing-marker":
            rewrite(source, lambda s: s.replace("# raw-binding: " + source["key"] + "\n", ""))
        elif fault == "duplicate-marker":
            rewrite(
                source,
                lambda s: s.replace(
                    "# raw-binding: " + source["key"],
                    ("# raw-binding: " + source["key"] + "\n") * 2,
                ),
            )
        elif fault == "missing-binding":
            source["registry"]["bindings"].clear()
        elif fault == "missa-common-alias":
            archives[body]["upstream"] = archives[body]["upstream"].replace("/horas/", "/missa/")
        elif fault == "office-conclusion":
            archives["prayers"]["upstream"] = "web/www/horas/Latin/Psalterium/Common/Prayers.txt"
        elif fault in {"missing-body-archive", "missing-ordo-archive"}:
            del archives[body if fault == "missing-body-archive" else "missa-ordo-44667ff"]
        elif fault == "missing-body-file":
            (source["root"] / archives[body]["path"]).unlink()
        elif fault == "archive-revision":
            archives[body]["revision"] = "0" * 40
        elif fault in {"duplicate-archive-identity", "duplicate-local-path"}:
            extra = copy.deepcopy(archives[body])
            if fault == "duplicate-local-path":
                extra["upstream"] = "web/www/horas/Latin/Commune/Other.txt"
            archives["duplicate"] = extra
        elif fault == "escape-local-path":
            archives[body]["path"] = "witnesses/raw/../escaped.txt"
        elif fault == "escaping-source-symlink":
            path = source["root"] / archives[body]["path"]
            outside = source["root"].parent / "outside.txt"
            outside.write_bytes(path.read_bytes())
            path.unlink()
            path.symlink_to(outside)
        else:
            raise AssertionError(fault)
        save_registry(source)
        if fault in {"transplanted-witness", "unknown-binding"}:
            with pytest.raises(raw_binding.BindingError, match=re.escape(message)):
                resolve(source)
        else:
            rejected_raw(source, message)


@pytest.mark.parametrize("role", ["selection", "inheritance", "body", "prayers", "ordo"])
@pytest.mark.parametrize("refresh", [False, True], ids=["old-digest", "refreshed-digest"])
@pytest.mark.parametrize("source", list(CASES), indirect=True)
def test_every_complete_component_byte_is_bound(source, role, refresh):
    with restored(source):
        key = {
            "selection": source["sections"][0][0],
            "inheritance": source["sections"][1][0],
            "body": source["sections"][-1][0],
            "prayers": "prayers",
            "ordo": "missa-ordo-44667ff",
        }[role]
        path = source["root"] / source["registry"]["archives"][key]["path"]
        path.write_bytes(path.read_bytes() + b"\n")
        if refresh:
            source["registry"]["archives"][key]["sha256"] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
            save_registry(source)
        rejected_raw(source, PINNED_OBJECT if refresh else "SHA-256 mismatch")


SOURCE_CASES = [
    "inheritance-cue",
    "remove-inheritance-cue",
    "dollar-cue",
    "remove-dollar-cue",
    "heading",
    "another-section",
    "formula",
    "response-prefix",
    "ordo-call",
    "ordo-rubric",
]


@pytest.mark.parametrize("fault", SOURCE_CASES)
@pytest.mark.parametrize("source", list(CASES), indirect=True)
def test_refreshing_registry_hash_cannot_admit_changed_source_context(source, fault):
    with restored(source):
        if fault in {"inheritance-cue", "remove-inheritance-cue"}:
            key, _, number, _ = source["sections"][0]
            replacement = "" if fault == "remove-inheritance-cue" else "@Commune/C8"
        elif fault in {"dollar-cue", "remove-dollar-cue", "heading", "another-section"}:
            key, heading, last, _ = source["sections"][-1]
            number = heading if fault == "heading" else last
            replacement = {
                "dollar-cue": "$Qui vivis",
                "remove-dollar-cue": "",
                "heading": "[Postcommunio]",
                "another-section": "[Secreta 2 loco]",
            }[fault]
        elif fault in {"formula", "response-prefix"}:
            key, number = "prayers", 96 if fault == "formula" else 97
            replacement = "r. Qui vivis." if fault == "formula" else "S. Amen."
        else:
            key, number = "missa-ordo-44667ff", 199 if fault == "ordo-call" else 202
            replacement = "&postcommunio" if fault == "ordo-call" else "!Altered rubric."
        record = source["registry"]["archives"][key]
        path = source["root"] / record["path"]
        lines = path.read_text().splitlines()
        assert lines[number - 1] != replacement
        lines[number - 1] = replacement
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        save_registry(source)
        rejected_raw(source, PINNED_OBJECT)


BODY_CASES = [
    "jesum",
    "qui",
    "sancti-comma",
    "proper-substantive",
    "omit-proper",
    "repeat-proper",
    "omit-formula",
    "repeat-amen",
    "reorder-pieces",
    "keep-r-prefix",
    "keep-R-prefix",
    "path-header",
]


@pytest.mark.parametrize("fault", BODY_CASES)
@pytest.mark.parametrize("source", list(CASES), indirect=True)
def test_literal_witness_cannot_be_normalized_or_recomposed(source, fault):
    with restored(source):
        changes = {
            "jesum": ("Jesum", "Iesum"),
            "qui": ("qui tecum", "Qui tecum"),
            "sancti-comma": ("Sancti Deus", "Sancti, Deus"),
            "proper-substantive": (
                ("Vírginis intercessióne", "Vírginis, Unigéniti tui Matris, intercessióne")
                if source["case"] == "maternity"
                else ("nostra devotiónis", "nostræ devotiónis")
            ),
            "omit-formula": (FORMULA, "Amen."),
            "repeat-amen": ("Amen.", "Amen. Amen."),
            "omit-proper": (source["literal"], FORMULA),
            "repeat-proper": (
                source["literal"],
                source["literal"].removesuffix(FORMULA) + source["literal"],
            ),
            "reorder-pieces": (
                source["literal"],
                FORMULA + " " + source["literal"].removesuffix(FORMULA),
            ),
            "keep-r-prefix": ("Per Dóminum nostrum Jesum", "r. Per Dóminum nostrum Jesum"),
            "keep-R-prefix": ("Amen.", "R. Amen."),
            "path-header": ("# path: ", "# path: wrong-context; "),
        }
        old, new = changes[fault]
        rewrite(source, lambda s: s.replace(old, new, 1))
        message = (
            "witness path declarations differ from bound evidence"
            if fault == "path-header"
            else "transcription differs from its exact Mass Secret reading"
        )
        rejected_raw(source, message)


@pytest.mark.parametrize(
    "old,new",
    [("Justórum,", "Iustórum,"), ("tuórum", "cunctórum")],
    ids=["literal-J", "literal-tuorum"],
)
@pytest.mark.parametrize("source", ["all-saints"], indirect=True)
def test_all_saints_distinct_literal_readings_are_not_replaced(source, old, new):
    with restored(source):
        rewrite(source, lambda s: s.replace(old, new, 1))
        rejected_raw(source, "transcription differs from its exact Mass Secret reading")


@pytest.mark.parametrize(
    "replacement", ["@Commune/C8", ""], ids=["wrong-reference", "omitted-reference"]
)
@pytest.mark.parametrize("source", ["maternity"], indirect=True)
def test_maternity_intermediate_common_reference_is_bound(source, replacement):
    with restored(source):
        record = source["registry"]["archives"]["common-c10"]
        path = source["root"] / record["path"]
        lines = path.read_text().splitlines()
        assert lines[216] == "@Commune/C11"
        lines[216] = replacement
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        save_registry(source)
        rejected_raw(source, PINNED_OBJECT)


@pytest.mark.parametrize("source", ["maternity"], indirect=True)
def test_maternity_literal_conclusion_does_not_gain_eundem(source):
    with restored(source):
        rewrite(
            source,
            lambda s: s.replace("Per Dóminum nostrum Jesum", "Per eúndem Dóminum nostrum Jesum", 1),
        )
        rejected_raw(source, "transcription differs from its exact Mass Secret reading")


@pytest.mark.parametrize("source", list(CASES), indirect=True)
def test_generic_contract_still_rejects_physical_office_to_mass_dollar_jump(source):
    with restored(source):
        sections = source["sections"]
        evidence = [
            {"archive": k, "first": h, "last": z, "section": "Secreta", "section_line": h}
            for k, h, z, _ in sections
        ]
        evidence.append(
            {
                "archive": "prayers",
                "first": 95,
                "last": 97,
                "section": "Per Dominum",
                "section_line": 95,
            }
        )
        refs = [
            {"archive": k, "line": z, "text": cue, "target": i + 1}
            for i, (k, _, z, cue) in enumerate(sections)
        ]
        k, h, _, _ = sections[-1]
        reading = [
            {"archive": k, "first": h + 1, "last": h + 1},
            {"archive": "prayers", "first": 96, "last": 97},
        ]
        source["registry"]["bindings"][source["key"]] = {
            "witness": f"witnesses/{source['text']}/do.txt",
            "revision": REVISION,
            "evidence": evidence,
            "references": refs,
            "reading": reading,
        }
        save_registry(source)
        rejected_raw(source, "reference points to a different source or section")


STRUCTURAL_CASES = [
    ("body-cue", "raw-reading-9 requires the complete literal Secret chain"),
    ("section-heading", "raw-reading-9 requires the complete literal Secret chain"),
    ("extra-section-text", "raw-reading-9 requires the complete literal Secret chain"),
    ("formula-heading", "raw-reading-9 requires the complete Mass conclusion and response"),
    ("formula-prefix", "raw-reading-9 requires the complete Mass conclusion and response"),
    ("response-prefix", "raw-reading-9 requires the complete Mass conclusion and response"),
    ("ordo-call", "raw-reading-9 requires the actual Mass Ordo Secret call"),
]


@pytest.mark.parametrize("fault,message", STRUCTURAL_CASES, ids=[r[0] for r in STRUCTURAL_CASES])
@pytest.mark.parametrize("source", list(CASES), indirect=True)
def test_structural_guards_after_explicit_test_only_profile_digest_change(
    source, monkeypatch, fault, message
):
    """Unit guard reachability only; these are never supported source profiles."""
    with restored(source), monkeypatch.context() as patch:
        key, heading, last, _ = source["sections"][-1]
        if fault.startswith("formula") or fault == "response-prefix":
            key = "prayers"
        elif fault == "ordo-call":
            key = "missa-ordo-44667ff"
        record = source["registry"]["archives"][key]
        path = source["root"] / record["path"]
        lines = path.read_text().splitlines()
        if fault == "body-cue":
            lines[last - 1] = "$Qui vivis"
        elif fault == "section-heading":
            lines[heading - 1] = "[Postcommunio]"
        elif fault == "extra-section-text":
            lines.insert(last, "Additional section text.")
        elif fault == "formula-heading":
            lines[94] = "[Qui vivis]"
        elif fault == "formula-prefix":
            lines[95] = lines[95].removeprefix("r. ")
        elif fault == "response-prefix":
            lines[96] = "S. Amen."
        elif fault == "ordo-call":
            lines[198] = "&postcommunio"
        else:
            raise AssertionError(fault)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        record["sha256"] = digest
        save_registry(source)
        # This monkeypatch is deliberately stronger than allowed DATA:
        # it bypasses only the closed expected-digest layer to reach the
        # subsequent structural guard, then restores that code constant.
        patch.setitem(raw_binding_mass_secrets.ARCHIVES, key, (record["upstream"], digest))
        rejected_raw(source, message)


GRAPH_CASES = [
    ("missing-inventory", "complete explicit source_dependencies declaration required"),
    ("empty-inventory", "raw-reading-9 requires exactly literal-reading and Mass-context uses"),
    ("null-inventory", "complete explicit source_dependencies declaration required"),
    ("extra-dependency", "raw-reading-9 requires exactly literal-reading and Mass-context uses"),
    ("wrong-context-text", "source use and document must address the same text"),
    ("missing-use", "unknown source use"),
    ("wrong-binding", "declared raw binding differs from registered resolution"),
    ("null-binding", "source requires its explicit exact raw binding"),
    ("swapped-use-ids", "source use has an incompatible role"),
    ("primary-print-role", "raw-reading-9 source-use role differs from its contribution"),
    ("context-text-role", "raw-reading-9 source-use role differs from its contribution"),
    ("primary-feast-hash", "raw-reading-9 source-use evidence differs from its contribution"),
    ("context-reading-hash", "raw-reading-9 source-use evidence differs from its contribution"),
    ("context-prayers-hash", "raw-reading-9 source-use evidence differs from its contribution"),
    ("other-edition", "supplemental source belongs to another edition"),
    ("other-revision", "digital item revision or kind differs from raw binding"),
    ("other-provider", "unsupported born-digital source requires its own evidence contract"),
    ("stale-transcript-digest", "transcription_sha256 differs from the complete bound transcript"),
]


@pytest.mark.parametrize("fault,message", GRAPH_CASES, ids=[r[0] for r in GRAPH_CASES])
@pytest.mark.parametrize("source", list(CASES), indirect=True)
def test_pending_graph_requires_each_real_contribution_and_recovers(source, fault, message):
    with restored(source):
        row, primary, context = witness(source), use(source), use(source, True)
        deps = row["source_dependencies"]
        if fault == "missing-inventory":
            del row["source_dependencies"]
        elif fault == "empty-inventory":
            deps["uses"] = []
        elif fault == "null-inventory":
            row["source_dependencies"] = None
        elif fault == "extra-dependency":
            extra = copy.deepcopy(context)
            extra["id"] += "-extra"
            source["graph"]["uses"].append(extra)
            deps["uses"] = sorted([context["id"], extra["id"]])
        elif fault == "wrong-context-text":
            context["address"]["text"] = "proprium.unrelated-secreta"
        elif fault == "missing-use":
            source["graph"]["uses"].remove(context)
        elif fault == "wrong-binding":
            deps["raw_binding"] = "another-binding"
        elif fault == "null-binding":
            deps["raw_binding"] = None
        elif fault == "swapped-use-ids":
            row["use"], deps["uses"] = context["id"], [primary["id"]]
        elif fault == "primary-print-role":
            primary["role"] = "direct_approved_print"
        elif fault == "context-text-role":
            context["role"] = "derived_digital_collation_aid"
        elif fault == "primary-feast-hash":
            primary["evidence_sha256"] = ARCHIVES[source["sections"][0][0]][1]
        elif fault == "context-reading-hash":
            context["evidence_sha256"] = primary["evidence_sha256"]
        elif fault == "context-prayers-hash":
            context["evidence_sha256"] = ARCHIVES["prayers"][1]
        elif fault == "other-edition":
            edition = copy.deepcopy(one(source["graph"]["editions"], context["edition"]))
            edition["id"] = "edition.unrelated"
            item = copy.deepcopy(one(source["graph"]["digital_items"], context["digital_item"]))
            item["id"], item["edition"] = "item.unrelated", edition["id"]
            source["graph"]["editions"].append(edition)
            source["graph"]["digital_items"].append(item)
            context["edition"], context["digital_item"] = edition["id"], item["id"]
        elif fault == "other-revision":
            one(source["graph"]["digital_items"], primary["digital_item"])["revision"] = "0" * 40
        elif fault == "other-provider":
            edition = one(source["graph"]["editions"], primary["edition"])
            work = copy.deepcopy(one(source["graph"]["works"], edition["work"]))
            work["id"] = "work.unrelated"
            source["graph"]["works"].append(work)
            edition["work"] = work["id"]
            one(source["graph"]["digital_items"], primary["digital_item"])["record_url"] = (
                "https://example.com/unrelated"
            )
        elif fault == "stale-transcript-digest":
            row["transcription_sha256"] = "0" * 64
        else:
            raise AssertionError(fault)
        rejected_subject(source, message)


@pytest.mark.parametrize(
    "fault", ["apparatus-entry", "apparatus-summary", "apparatus-hash", "selected-word"]
)
@pytest.mark.parametrize("source", list(CASES), indirect=True)
def test_collation_identity_cannot_be_resealed_by_source_resolution(source, fault):
    with restored(source):
        coll = one(source["graph"]["collations"], f"collation.{source['text']}.mr1962-do44667ff")
        if fault in {"apparatus-entry", "apparatus-summary"}:
            path = source["witness"].parent / "apparatus.json"
            app = json.loads(path.read_text())
            if fault == "apparatus-entry":
                app["adjudicated"][0]["ruling"] += " Changed."
            else:
                app["summary"]["entries"] += 1
            put(path, app)
        elif fault == "apparatus-hash":
            coll["apparatus_sha256"] = "0" * 64
        else:
            source["doc"]["segments"][0]["words"][0]["form"] += "x"
        subjects = {
            w["id"]: witness_subject(source["root"], w, source["graph"], source["doc"])
            for w in source["graph"]["witnesses"]
        }
        message = (
            "selected_text_sha256 differs"
            if fault == "selected-word"
            else "apparatus_sha256 differs"
        )
        with pytest.raises(ValueError, match=message):
            collation_subject(source["root"], coll, source["doc"], subjects)


@pytest.mark.parametrize("source", list(CASES), indirect=True)
def test_removing_both_marker_and_registry_cannot_hide_from_pending_graph(source):
    with restored(source):
        rewrite(source, lambda s: s.replace("# raw-binding: " + source["key"] + "\n", ""))
        source["registry"]["bindings"].clear()
        save_registry(source)
        assert resolve(source) is None  # legacy raw resolution alone is not acceptance
        rejected_subject(source, "declared raw binding differs from registered resolution")


@pytest.mark.parametrize("source", list(CASES), indirect=True)
def test_text_only_contract_is_checked_before_performer_access(source, monkeypatch):
    healthy(source)
    original = raw_binding.resolve_binding

    class TextOnly:
        def __init__(self, reading):
            self.source = reading.source

        @property
        def spans(self):
            pytest.fail("text-only Mass Secret reached performer spans")

        @property
        def fragments(self):
            pytest.fail("text-only Mass Secret reached performer fragments")

    def checked(path, root):
        reading = original(path, root)
        return TextOnly(reading) if reading is not None else None

    monkeypatch.setattr(attribute, "CORPUS", source["root"])
    monkeypatch.setattr(attribute, "resolve_binding", checked)
    with pytest.raises(raw_binding.BindingError, match="supports textual identity only"):
        attribute._source_ranges(source["text"])
    current = attribute._actor_sources(source["text"])
    assert current.scope == "RAW_TEXT_ONLY" and current.units == ()
    assert current.reasons == ("TEXT_ONLY_CONTRACT:do.txt: raw-reading-9",)
    assert attribute.marked_lines(source["text"]) == []
    assert all((ROOT / name).read_bytes() == raw for name, raw in source["originals"].items())


@pytest.mark.parametrize("source", list(CASES), indirect=True)
def test_returned_source_objects_do_not_alias_snapshot_or_next_reading(source):
    expected, _ = healthy(source)
    before = files(source["root"])
    snapshot = raw_binding.RawBindingSnapshot(source["root"])
    first = snapshot.resolve(source["witness"])
    assert first is not None
    first.source["binding"]["profile"] = "changed"
    first.source["archives"]["prayers"]["sha256"] = "0" * 64
    first.source["profile"]["sections"].clear()
    first.source["profile"]["archive_roles"].clear()
    first.source["resolved_literal_composition"]["context"].clear()
    first.source["resolved_literal_composition"]["pieces"].clear()
    assert snapshot.resolve(source["witness"]).source == expected
    assert resolve(source).source == expected and files(source["root"]) == before
