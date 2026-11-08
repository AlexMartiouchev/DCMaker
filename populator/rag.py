"""Loading the RAG seed file into RagDocument rows.

The seed (prompts/rag/rag_seed.json) holds exemplar collections plus three
reference blocks. Every exemplar's `payload` must validate against the same
Pydantic schema the generator uses, so a seed that loads is a seed the
engine can learn from. Loading is idempotent: rows are upserted by
`external_id`, so rerunning after editing the file only touches what changed.
"""

import json
from pathlib import Path

from django.conf import settings
from django.db import transaction
from pydantic import ValidationError

from .generation.schemas import (
    GeneratedCharacter,
    GeneratedFaction,
    GeneratedLocation,
    MobArchetype,
)
from .models import RagDocument

SEED_SOURCE = "seed"

# seed key -> (doc_type, schema the payload must satisfy)
COLLECTIONS = {
    "locations": (RagDocument.DocType.LOCATION, GeneratedLocation),
    "factions": (RagDocument.DocType.FACTION, GeneratedFaction),
    "characters": (RagDocument.DocType.CHARACTER, GeneratedCharacter),
    "mob_archetypes": (RagDocument.DocType.MOB_ARCHETYPE, MobArchetype),
}

# Stored whole, one row each, as doc_type "reference".
REFERENCE_BLOCKS = ("meta", "taxonomy", "ip_guardrails")

_ID_MAX = RagDocument._meta.get_field("external_id").max_length


class SeedError(Exception):
    """The seed file cannot be loaded. `problems` lists every reason."""

    def __init__(self, problems):
        self.problems = list(problems)
        super().__init__("; ".join(self.problems))


class _DryRun(Exception):
    """Raised inside the transaction to roll it back."""


def default_seed_path() -> Path:
    return Path(settings.BASE_DIR) / "prompts" / "rag" / "rag_seed.json"


def _validation_summary(exc: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(str(part) for part in err['loc'])}: {err['msg']}"
        for err in exc.errors()
    )


def parse_seed(data: dict) -> list[dict]:
    """Validate the seed and return documents ready to store.

    Each document is {external_id, doc_type, metadata, payload}. Metadata is
    every key of an entry except `id` and `payload`. Raises SeedError listing
    all problems, so one run shows everything that needs fixing.
    """
    problems: list[str] = []
    docs: list[dict] = []
    seen: set[str] = set()

    for key, (doc_type, schema) in COLLECTIONS.items():
        for item in data.get(key, []):
            external_id = item.get("id")
            if not external_id or "payload" not in item:
                problems.append(f"{key}: entry without an id or a payload")
                continue
            if len(external_id) > _ID_MAX:
                problems.append(f"{external_id}: id longer than {_ID_MAX} characters")
                continue
            if external_id in seen:
                problems.append(f"{external_id}: duplicate id")
                continue
            seen.add(external_id)
            try:
                schema.model_validate(item["payload"])
            except ValidationError as exc:
                problems.append(f"{external_id}: {_validation_summary(exc)}")
                continue
            docs.append(
                {
                    "external_id": external_id,
                    "doc_type": doc_type.value,
                    "metadata": {
                        k: v for k, v in item.items() if k not in ("id", "payload")
                    },
                    "payload": item["payload"],
                }
            )

    for block in REFERENCE_BLOCKS:
        if block not in data:
            continue
        if not isinstance(data[block], dict):
            problems.append(f"{block}: reference block must be an object")
            continue
        docs.append(
            {
                "external_id": block,
                "doc_type": RagDocument.DocType.REFERENCE.value,
                "metadata": {},
                "payload": data[block],
            }
        )

    ids = {
        doc_type: {d["external_id"] for d in docs if d["doc_type"] == doc_type}
        for doc_type in ("location", "faction", "character")
    }
    for doc in docs:
        meta = doc["metadata"]
        if doc["doc_type"] == "faction" and meta.get("location_id") not in ids["location"]:
            problems.append(f"{doc['external_id']}: unknown location_id {meta.get('location_id')!r}")
        if doc["doc_type"] in ("character", "mob_archetype") and meta.get("faction_id") not in ids["faction"]:
            problems.append(f"{doc['external_id']}: unknown faction_id {meta.get('faction_id')!r}")
        if doc["doc_type"] == "character":
            for rel in meta.get("relationships", []):
                if rel.get("to") not in ids["character"]:
                    problems.append(f"{doc['external_id']}: relationship to unknown {rel.get('to')!r}")

    if problems:
        raise SeedError(problems)
    return docs


def load_docs(docs: list[dict], *, prune: bool = False, dry_run: bool = False) -> dict:
    """Upsert documents by external_id and return counts.

    All or nothing: a conflict aborts the whole load. With prune, seed-sourced
    rows missing from `docs` are deleted; rows from other sources never are.
    With dry_run the counts are real but nothing is written.
    """
    counts = {"created": 0, "updated": 0, "unchanged": 0, "pruned": 0}
    try:
        with transaction.atomic():
            existing = {row.external_id: row for row in RagDocument.objects.all()}
            for doc in docs:
                row = existing.get(doc["external_id"])
                if row is None:
                    RagDocument.objects.create(source=SEED_SOURCE, **doc)
                    counts["created"] += 1
                elif row.source != SEED_SOURCE:
                    raise SeedError(
                        [f"{doc['external_id']}: already exists from source {row.source!r}; not overwriting"]
                    )
                elif (row.doc_type, row.metadata, row.payload) == (
                    doc["doc_type"], doc["metadata"], doc["payload"],
                ):
                    counts["unchanged"] += 1
                else:
                    row.doc_type = doc["doc_type"]
                    row.metadata = doc["metadata"]
                    row.payload = doc["payload"]
                    row.save()
                    counts["updated"] += 1

            if prune:
                stale = RagDocument.objects.filter(source=SEED_SOURCE).exclude(
                    external_id__in=[d["external_id"] for d in docs]
                )
                counts["pruned"] = stale.count()
                stale.delete()

            if dry_run:
                raise _DryRun
    except _DryRun:
        pass
    return counts


def load_seed_file(path, *, prune: bool = False, dry_run: bool = False) -> dict:
    """Read, validate and load a seed file. FileNotFoundError propagates."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SeedError([f"not valid JSON: {exc}"]) from exc
    return load_docs(parse_seed(data), prune=prune, dry_run=dry_run)
