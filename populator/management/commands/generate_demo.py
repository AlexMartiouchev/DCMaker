"""Generate and persist a complete demo setting.

Usage:
    python manage.py generate_demo "A drowned cathedral city" --factions 2 --sheets

Drives the whole pipeline step-by-step through the orchestrator's save
functions, persisting after every successful step — if a step dies, the
run stops but everything already saved stays saved (rerun costs only
the missing pieces).
"""

from django.core.management.base import BaseCommand

from populator import orchestrator
from populator.generation import generate as engine
from populator.generation.schemas import RankTier


class Command(BaseCommand):
    help = "Generate a full demo setting (location, factions, rosters) and save it to the database."

    def add_arguments(self, parser):
        parser.add_argument("concept", help="The location concept to build from")
        parser.add_argument("--party-level", type=int, default=6)
        parser.add_argument("--factions", type=int, default=3)
        parser.add_argument(
            "--sheets",
            action="store_true",
            help="Also generate combat sheets for leadership-tier characters",
        )

    def handle(self, *args, **options):
        concept = options["concept"]

        self.stdout.write(f"Generating location for: {concept!r} ...")
        gen_location = engine.generate_location(concept)
        location = orchestrator.save_location(
            gen_location, party_level=options["party_level"]
        )
        self.stdout.write(
            self.style.SUCCESS(f"  Saved location #{location.pk}: {location.name}")
        )

        self.stdout.write(f"Generating {options['factions']} factions ...")
        gen_factions = engine.generate_factions(
            gen_location, num_factions=options["factions"]
        )

        for gen_faction in gen_factions:
            faction = orchestrator.save_faction(location, gen_faction)
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Saved faction #{faction.pk}: {faction.name} "
                    f"({len(gen_faction.hierarchy)} ranks)"
                )
            )

            try:
                roster = engine.fill_roster(
                    gen_location, gen_faction, gen_faction.hierarchy
                )
                for gen_character in roster:
                    character = orchestrator.save_character(faction, gen_character)
                    self.stdout.write(
                        f"    {character.rank_title}: {character.name}"
                    )

                    if options["sheets"] and character.rank_tier == RankTier.LEADERSHIP:
                        sheet = engine.generate_combat_sheet(
                            gen_character,
                            gen_faction,
                            party_level=options["party_level"],
                            tier=RankTier.LEADERSHIP,
                        )
                        orchestrator.save_combat_sheet(character, sheet)
                        self.stdout.write(
                            f"      statted: {sheet.profession}, "
                            f"HP {sheet.stats.hp}, AC {sheet.stats.ac}"
                        )
            except Exception as exc:  # keep other factions alive per failure policy
                self.stderr.write(
                    self.style.ERROR(
                        f"  Roster for {faction.name} failed ({exc}); "
                        "faction kept, characters can be regenerated later."
                    )
                )

        self.stdout.write(self.style.SUCCESS(f"Done. Location #{location.pk} is ready."))
