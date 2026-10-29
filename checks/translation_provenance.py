"""Every vernacular translation names its public provenance state.

A citation inventory cannot cover an uncited translation, and an absent
citation is itself a claim: the wording is the edition's own. The public
provenance ledger therefore covers every `verse segment × language` site and
binds its state to hashes of both source and target. A translation edit cannot
inherit an old review state silently, and deleting a citation cannot delete the
site.

The ledger deliberately contains no drafting notes or comparison text. It says
only what a public reader of the corpus needs to know: origin, review level,
whether exact familiarity is being protected, and which two strings were
classified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from build_reader import bibliography, store
from checks.participation_performance import source_fields

WORDING_BASIS = "historical_wording_basis"
ORIGINS = frozenset(
    ("working-unsettled", "own", "public-domain", "traditional", "trivial", "mixed")
)
SCHEMA = "1.1.0"
LEGACY_SCHEMA = "1.0.0"
REVIEWS = frozenset(("working", "internally-reviewed", "expert-reviewed"))

PROTECTED_PL_SEGMENTS = {
    "ordinarium.deus-tu-conversus": frozenset({"s08", "s09"}),
    "ordinarium.evangelium-ultimum": frozenset({"s02", "s03"}),
    "ordinarium.ite-missa-est": frozenset({"s02", "s03"}),
    "ordinarium.pax-domini": frozenset({"s03"}),
    "ordinarium.praefatio-dialogus": frozenset({"s02", "s03"}),
    "ordinarium.qui-dixisti": frozenset({"s09"}),
    "ordinarium.agnus-dei-defunctorum": frozenset({"s01", "s02", "s03"}),
    "ordinarium.ite-missa-est-defunctorum": frozenset({"s01", "s02", "s03", "s04"}),
    "ordinarium.ite-missa-est-paschale": frozenset({"s02", "s03", "s05", "s06"}),
    "ordinarium.iube-domne-benedicere": frozenset({"s03"}),
    "ordinarium.iube-domne-benedicere-in-passione": frozenset({"s03"}),
    "proprium.vigilia-paschalis-laudes-psalmus": frozenset({"s07", "s08"}),
    "proprium.vigilia-paschalis-laudes-canticum": frozenset({"s15", "s16"}),
}

# Fixed Gloria Patri embedded in Polish Introits; independent of the current target wording.
PROTECTED_PL_INTROIT_SEGMENTS = {
    "proprium.annuntiatio-beatae-mariae-virginis-extra-tempus-paschale-introitus": frozenset(
        {"s01"}
    ),
    "proprium.annuntiatio-beatae-mariae-virginis-introitus": frozenset({"s01"}),
    "proprium.ascensio-domini-introitus": frozenset({"s01"}),
    "proprium.assumptio-beatae-mariae-virginis-introitus": frozenset({"s01"}),
    "proprium.beata-maria-virgo-regina-extra-tempus-paschale-introitus": frozenset({"s01"}),
    "proprium.beata-maria-virgo-regina-introitus": frozenset({"s01"}),
    "proprium.beatae-mariae-virginis-a-rosario-introitus": frozenset({"s01"}),
    "proprium.cathedra-sancti-petri-introitus": frozenset({"s01"}),
    "proprium.corporis-christi-introitus": frozenset({"s03"}),
    "proprium.d-n-iesu-christi-regis-introitus": frozenset({"s01"}),
    "proprium.dedicatio-archibasilicae-sanctissimi-salvatoris-introitus": frozenset({"s01"}),
    "proprium.dedicatio-sancti-michaelis-archangeli-introitus": frozenset({"s01"}),
    "proprium.dominica-i-adventus-introitus": frozenset({"s03"}),
    "proprium.dominica-i-in-quadragesima-introitus": frozenset({"s01"}),
    "proprium.dominica-i-post-epiphaniam-introitus": frozenset({"s01"}),
    "proprium.dominica-ii-adventus-introitus": frozenset({"s03"}),
    "proprium.dominica-ii-in-quadragesima-introitus": frozenset({"s01"}),
    "proprium.dominica-ii-post-epiphaniam-introitus": frozenset({"s01"}),
    "proprium.dominica-ii-post-pascha-introitus": frozenset({"s01"}),
    "proprium.dominica-ii-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-iii-adventus-introitus": frozenset({"s03"}),
    "proprium.dominica-iii-in-quadragesima-introitus": frozenset({"s01"}),
    "proprium.dominica-iii-post-epiphaniam-introitus": frozenset({"s01"}),
    "proprium.dominica-iii-post-pascha-introitus": frozenset({"s01"}),
    "proprium.dominica-iii-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-in-albis-introitus": frozenset({"s01"}),
    "proprium.dominica-in-quinquagesima-introitus": frozenset({"s01"}),
    "proprium.dominica-in-septuagesima-introitus": frozenset({"s01"}),
    "proprium.dominica-in-sexagesima-introitus": frozenset({"s01"}),
    "proprium.dominica-infra-octavam-nativitatis-introitus": frozenset({"s01"}),
    "proprium.dominica-iv-adventus-introitus": frozenset({"s03"}),
    "proprium.dominica-iv-in-quadragesima-introitus": frozenset({"s01"}),
    "proprium.dominica-iv-post-pascha-introitus": frozenset({"s01"}),
    "proprium.dominica-iv-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-ix-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-pentecostes-introitus": frozenset({"s01"}),
    "proprium.dominica-post-ascensionem-introitus": frozenset({"s01"}),
    "proprium.dominica-resurrectionis-introitus": frozenset({"s01"}),
    "proprium.dominica-v-post-pascha-introitus": frozenset({"s01"}),
    "proprium.dominica-v-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-vi-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-vii-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-viii-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-x-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-xi-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-xii-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-xiii-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-xiv-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-xix-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-xv-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-xvi-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-xvii-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-xviii-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-xx-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-xxi-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-xxii-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.dominica-xxiii-post-pentecosten-introitus": frozenset({"s01"}),
    "proprium.epiphania-domini-introitus": frozenset({"s01"}),
    "proprium.exaltatio-sanctae-crucis-introitus": frozenset({"s01"}),
    "proprium.immaculata-conceptio-introitus": frozenset({"s01"}),
    "proprium.immaculatum-cor-beatae-mariae-virginis-introitus": frozenset({"s01"}),
    "proprium.maternitas-beatae-mariae-virginis-introitus": frozenset({"s01"}),
    "proprium.nativitas-domini-in-aurora-introitus": frozenset({"s01"}),
    "proprium.nativitas-domini-in-die-introitus": frozenset({"s01"}),
    "proprium.nativitas-domini-in-nocte-introitus": frozenset({"s01"}),
    "proprium.nativitas-sancti-ioannis-baptistae-introitus": frozenset({"s01"}),
    "proprium.omnium-sanctorum-introitus": frozenset({"s01"}),
    "proprium.pretiosissimi-sanguinis-domini-nostri-iesu-christi-introitus": frozenset({"s01"}),
    "proprium.sacratissimi-cordis-iesu-introitus": frozenset({"s03"}),
    "proprium.sancta-familia-introitus": frozenset({"s01"}),
    "proprium.sanctae-annae-matris-beatae-mariae-virginis-introitus": frozenset({"s01"}),
    "proprium.sancti-iacobi-apostoli-introitus": frozenset({"s01"}),
    "proprium.sancti-ioachim-confessoris-introitus": frozenset({"s01"}),
    "proprium.sancti-ioannis-apostoli-et-evangelistae-introitus": frozenset({"s01"}),
    "proprium.sancti-ioseph-opificis-introitus": frozenset({"s01"}),
    (
        "proprium.sancti-ioseph-sponsi-beatae-mariae-virginis-extra-tempus-paschale-introitus"
    ): frozenset({"s01"}),
    "proprium.sancti-ioseph-sponsi-beatae-mariae-virginis-introitus": frozenset({"s01"}),
    "proprium.sancti-laurentii-martyris-introitus": frozenset({"s01"}),
    "proprium.sancti-marci-evangelistae-introitus": frozenset({"s01"}),
    "proprium.sancti-matthaei-apostoli-et-evangelistae-introitus": frozenset({"s01"}),
    "proprium.sancti-petri-et-pauli-apostolorum-introitus": frozenset({"s01"}),
    "proprium.sancti-stephani-protomartyris-introitus": frozenset({"s01"}),
    "proprium.sanctissimae-trinitatis-introitus": frozenset({"s03"}),
    "proprium.sanctissimi-nominis-iesu-introitus": frozenset({"s01"}),
    "proprium.sanctorum-innocentium-martyrum-introitus": frozenset({"s01"}),
    "proprium.sanctorum-philippi-et-iacobi-apostolorum-introitus": frozenset({"s01"}),
    "proprium.septem-dolorum-beatae-mariae-virginis-introitus": frozenset({"s01"}),
    "proprium.transfiguratio-domini-introitus": frozenset({"s01"}),
    "proprium.vigilia-nativitatis-introitus": frozenset({"s01"}),
    "proprium.vigilia-pentecostes-introitus": frozenset({"s01"}),
    "proprium.visitatio-beatae-mariae-virginis-introitus": frozenset({"s01"}),
}

PROTECTED_EN_SEGMENTS = {
    "ordinarium.ite-missa-est-defunctorum": frozenset({"s03", "s04"}),
    "ordinarium.iube-domne-benedicere": frozenset({"s03"}),
    "ordinarium.iube-domne-benedicere-in-passione": frozenset({"s03"}),
}

PROTECTED_PL_TEXTS = frozenset(
    {
        "defunctorum.requiem-aeternam",
        "litaniae.lauretanae",
        "litaniae.sacratissimi-cordis-iesu",
        "litaniae.sanctissimi-nominis-iesu",
        "orationes.angelus-domini",
        "orationes.ave-maria",
        "orationes.gloria-patri",
        "orationes.magnificat",
        "orationes.anima-christi",
        "orationes.benedic-domine",
        "orationes.memorare",
        "orationes.pater-noster",
        "orationes.regina-caeli",
        "orationes.salve-regina",
        "orationes.sancte-michael",
        "orationes.signum-crucis",
        "orationes.sub-tuum-praesidium",
        "orationes.symbolum-apostolorum",
        "orationes.te-deum",
        "ordinarium.agnus-dei",
        "ordinarium.confiteor",
        "ordinarium.confiteor-sacerdotis",
        "ordinarium.credo",
        "ordinarium.gloria",
        "ordinarium.kyrie",
        "ordinarium.pater-noster",
        "ordinarium.sanctus",
        # The Paschal pair contains the inherited Ave greeting. Protection
        # does not attribute its separate Virga Iesse verse to that formula.
        "proprium.annuntiatio-beatae-mariae-virginis-alleluia",
        "proprium.annuntiatio-beatae-mariae-virginis-extra-tempus-paschale-introitus",
        "proprium.annuntiatio-beatae-mariae-virginis-introitus",
        "proprium.annuntiatio-beatae-mariae-virginis-extra-tempus-paschale-offertorium",
        "proprium.annuntiatio-beatae-mariae-virginis-offertorium",
        "proprium.dominica-iv-adventus-offertorium",
        "proprium.immaculata-conceptio-offertorium",
    }
)

PROTECTED_EN_TEXTS = frozenset(
    {
        "defunctorum.requiem-aeternam",
        "orationes.angelus-domini",
        "orationes.ave-maria",
        "orationes.gloria-patri",
        "orationes.pater-noster",
        "orationes.regina-caeli",
        "orationes.salve-regina",
        "orationes.sancte-michael",
        "orationes.signum-crucis",
        "orationes.sub-tuum-praesidium",
        "orationes.symbolum-apostolorum",
        "orationes.te-deum",
        "ordinarium.confiteor",
        "ordinarium.confiteor-sacerdotis",
        "ordinarium.kyrie",
        "ordinarium.pater-noster",
        "proprium.annuntiatio-beatae-mariae-virginis-alleluia",
        "proprium.annuntiatio-beatae-mariae-virginis-extra-tempus-paschale-introitus",
        "proprium.annuntiatio-beatae-mariae-virginis-introitus",
        "proprium.annuntiatio-beatae-mariae-virginis-extra-tempus-paschale-offertorium",
        "proprium.annuntiatio-beatae-mariae-virginis-offertorium",
        "proprium.dominica-iv-adventus-offertorium",
        "proprium.immaculata-conceptio-offertorium",
    }
)


def canonical_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def source_payload(segment: dict) -> dict:
    """Source-bearing fields whose change makes a translation review stale."""
    return {
        "id": segment["id"],
        "speaker": segment.get("speaker"),
        "voice": segment.get("voice"),
        **source_fields(segment),
        **({"delivery": segment["delivery"]} if "delivery" in segment else {}),
        # Preserve exact legacy payloads when no pair is present. Including
        # the explicit ranges binds placement as well as the displayed text;
        # shape errors are reported by the neutral/lint gates, not normalized.
        **({"parentheses": segment["parentheses"]} if "parentheses" in segment else {}),
        "words": [
            {
                key: word[key]
                for key in (
                    "id",
                    "form",
                    "post",
                    "lemma",
                    "morph",
                    "head",
                    "clause_head",
                    "substantive",
                    "ellipsis",
                )
                if key in word
            }
            for word in segment.get("words", [])
        ],
    }


def protected(text_id: str, language: str, segment_id: str | None = None) -> bool:
    if language == "pl":
        return (
            text_id in PROTECTED_PL_TEXTS
            or segment_id in PROTECTED_PL_SEGMENTS.get(text_id, ())
            or segment_id in PROTECTED_PL_INTROIT_SEGMENTS.get(text_id, ())
        )
    if language == "en":
        return text_id in PROTECTED_EN_TEXTS or segment_id in PROTECTED_EN_SEGMENTS.get(text_id, ())
    return False


def wording_bases(uses: list, language: str) -> tuple[set[str], set[str]]:
    """Sites and texts that a retained use names as a page's wording basis."""
    sites: set[str] = set()
    texts: set[str] = set()
    for use in uses:
        if (
            use.get("decision") not in {"RETAIN", "RETAIN_WITH_CORRECTION"}
            or use.get("role") != WORDING_BASIS
        ):
            continue
        address = use.get("address") or {}
        if address.get("kind") == "segment":
            sites.add(f"{address.get('text')}.{address.get('segment')}.{language}")
        elif address.get("kind") == "text":
            texts.add(str(address.get("text")))
    return sites, texts


def corpus_sites(corpus: Path) -> dict[str, dict]:
    graph, languages = bibliography.load(corpus)
    decisions = bibliography.LegacyCitationDecisions(graph, languages)
    bases = {
        language: wording_bases(package.get("uses") or [], language)
        for language, package in languages.items()
    }
    sites: dict[str, dict] = {}
    for doc, layers in store.all_texts(corpus):
        for segment in doc["segments"]:
            if segment["type"] != "verse":
                continue
            for language, layer in sorted(layers.items()):
                localized = (layer.get("segments") or {}).get(segment["id"]) or {}
                target = localized.get("translation")
                if not isinstance(target, str):
                    continue
                site = f"{doc['id']}.{segment['id']}.{language}"
                cited_sites, cited_texts = bases[language]
                sites[site] = {
                    "site": site,
                    "text": doc["id"],
                    "segment": segment["id"],
                    "language": language,
                    "familiar_core": protected(doc["id"], language, segment["id"]),
                    "source_sha256": canonical_hash(source_payload(segment)),
                    "target_sha256": canonical_hash(target),
                    # Only genuinely unmapped legacy attachments retain the
                    # compatibility fallback. A mapped comparator or rejected
                    # use cannot masquerade as an inherited wording basis.
                    # Mixed origin needs a real retained normalized basis, not legacy fallback.
                    "has_retained_wording_basis": (site in cited_sites or doc["id"] in cited_texts),
                    "has_wording_citations": decisions.has_unmapped_citation(
                        f"languages/{language}/texts/{doc['id'].replace('.', '/', 1)}.json",
                        ("segments", segment["id"], "translation_citations"),
                        localized.get("translation_citations") or [],
                    )
                    or site in cited_sites
                    or doc["id"] in cited_texts,
                }
    return sites


def load(corpus: Path) -> tuple[dict, list[str]]:
    by_site: dict[str, dict] = {}
    errors: list[str] = []
    for language in store.language_ids(corpus):
        path = corpus / "languages" / language / "translation-provenance.json"
        where = str(path.relative_to(corpus))
        if not path.exists():
            errors.append(f"{where} is missing")
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("schema_version") not in {LEGACY_SCHEMA, SCHEMA}:
            errors.append(f"{where}: schema_version must be {LEGACY_SCHEMA!r} or {SCHEMA!r}")
        if doc.get("language") != language:
            errors.append(f"{where}: language does not match its directory")
        if doc.get("status") != "working-edition":
            errors.append(f"{where}: status must be 'working-edition'")
        entries = doc.get("sites")
        if not isinstance(entries, list):
            errors.append(f"{where}: sites must be a list")
            continue
        for entry in entries:
            site = entry.get("site") if isinstance(entry, dict) else None
            if (
                isinstance(entry, dict)
                and entry.get("origin") == "mixed"
                and doc.get("schema_version") != SCHEMA
            ):
                errors.append(f"{site}: origin=mixed requires schema_version={SCHEMA!r}")
            if site in by_site:
                errors.append(f"{where}: duplicate site key {site!r}")
            elif site is not None:
                by_site[site] = entry
    return by_site, errors


def check(corpus: Path) -> tuple[list[str], dict[str, int]]:
    current = corpus_sites(corpus)
    recorded, errors = load(corpus)
    missing = sorted(set(current) - set(recorded))
    orphaned = sorted(set(recorded) - set(current))
    if missing:
        errors.append(
            f"translation provenance: {len(missing)} site(s) missing; first={missing[:5]}"
        )
    if orphaned:
        errors.append(
            f"translation provenance: {len(orphaned)} orphaned site(s); first={orphaned[:5]}"
        )

    tally: Counter[str] = Counter()
    for site in sorted(set(current) & set(recorded)):
        actual = current[site]
        entry = recorded[site]
        origin = entry.get("origin")
        review = entry.get("review")
        tally[str(origin)] += 1
        if origin not in ORIGINS:
            errors.append(f"{site}: unknown origin {origin!r}")
        if review not in REVIEWS:
            errors.append(f"{site}: unknown review level {review!r}")
        for key in ("text", "segment", "language", "familiar_core"):
            if entry.get(key) != actual[key]:
                errors.append(f"{site}: stale or incorrect {key}")
        for key in ("source_sha256", "target_sha256"):
            if entry.get(key) != actual[key]:
                errors.append(f"{site}: stale {key}")
        cited = actual["has_wording_citations"]
        if origin in {"own", "trivial"} and cited:
            errors.append(f"{site}: origin={origin} cannot carry a wording citation")
        if origin in {"public-domain", "traditional"} and not cited:
            errors.append(f"{site}: origin={origin} requires a wording citation")
        if origin == "mixed" and not actual["has_retained_wording_basis"]:
            errors.append(f"{site}: origin=mixed requires a retained {WORDING_BASIS} use")
        if origin == "working-unsettled" and review != "working":
            errors.append(f"{site}: unsettled origin cannot claim review={review}")
    return errors, dict(sorted(tally.items()))


def initialize(corpus: Path, language: str) -> int:
    if language not in store.language_ids(corpus):
        print(f"refusing to initialize unknown language {language!r}")
        return 1
    path = corpus / "languages" / language / "translation-provenance.json"
    if path.exists():
        print(f"refusing to overwrite {path.name}")
        return 1
    sites = {
        site: value for site, value in corpus_sites(corpus).items() if value["language"] == language
    }
    entries = []
    for site in sorted(sites):
        actual = sites[site]
        entries.append(
            {key: actual[key] for key in ("site", "text", "segment", "language", "familiar_core")}
            | {
                "origin": "working-unsettled",
                "review": "working",
                "source_sha256": actual["source_sha256"],
                "target_sha256": actual["target_sha256"],
            }
        )
    path.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA,
                "language": language,
                "status": "working-edition",
                "sites": entries,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"translation provenance initialized — sites={len(entries)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initialize", action="store_true")
    parser.add_argument("--language")
    args = parser.parse_args()
    corpus = Path(__file__).resolve().parent.parent
    if args.initialize:
        if not args.language:
            parser.error("--initialize requires --language")
        return initialize(corpus, args.language)
    errors, tally = check(corpus)
    for error in errors:
        print(f"ERROR: {error}")
    print(
        f"TRANSLATION PROVENANCE sites={sum(tally.values())} "
        + " ".join(f"{key}={value}" for key, value in tally.items())
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
