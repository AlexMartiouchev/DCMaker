"""Load the RAG seed file into the RagDocument table.

Usage:
    python manage.py load_rag_seed
    python manage.py load_rag_seed --dry-run
    python manage.py load_rag_seed --file path/to/seed.json --prune

Safe to rerun: rows are upserted by their seed id, so only changed entries
are written. Every exemplar is validated against the generation schemas
first, and a single problem aborts the whole load (nothing half-loaded).
Costs nothing: no API calls.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from populator import rag


class Command(BaseCommand):
    help = "Load the RAG seed file (exemplars and reference blocks) into the RagDocument table."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            help="Seed JSON to load (default: prompts/rag/rag_seed.json)",
        )
        parser.add_argument(
            "--prune",
            action="store_true",
            help="Delete seed-sourced rows that are no longer in the file",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Validate and report what would change, writing nothing",
        )

    def handle(self, *args, **options):
        path = Path(options["file"]) if options["file"] else rag.default_seed_path()
        try:
            counts = rag.load_seed_file(
                path, prune=options["prune"], dry_run=options["dry_run"]
            )
        except FileNotFoundError:
            raise CommandError(f"Seed file not found: {path}")
        except rag.SeedError as exc:
            lines = "\n".join(f"  - {problem}" for problem in exc.problems)
            raise CommandError(f"Seed file could not be loaded:\n{lines}")

        prefix = "[dry run] " if options["dry_run"] else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"{prefix}{path.name}: "
                f"{counts['created']} created, {counts['updated']} updated, "
                f"{counts['unchanged']} unchanged, {counts['pruned']} pruned"
            )
        )
