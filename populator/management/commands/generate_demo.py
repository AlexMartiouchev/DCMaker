"""Generate and persist a complete demo setting.

Usage:
    python manage.py generate_demo "A drowned cathedral city" --factions 2

Drives the whole pipeline step-by-step through the orchestrator's save
functions, persisting after every successful step — if a step dies, the
run stops but everything already saved stays saved (rerun costs only
the missing pieces).

Every character is fully statted by default: named characters get
individual sheets scaled to their hierarchy level; each mob archetype
gets one shared sheet for all its copies. --skip-sheets makes cheap
test runs possible.
"""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from populator import orchestrator
from populator.generation import generate as engine
from populator.generation.schemas import RankTier
from populator.models import Campaign


class Command(BaseCommand):
    help = "Generate a full demo setting (location, factions, rosters, sheets) and save it to the database."

    def add_arguments(self, parser):
        parser.add_argument("concept", help="The location concept to build from")
        parser.add_argument("--party-level", type=int, default=6)
        parser.add_argument("--factions", type=int, default=3)
        parser.add_argument(
            "--skip-sheets",
            action="store_true",
            help="Skip combat sheet generation (cheaper test runs)",
        )

    def handle(self, *args, **options):
        concept = options["concept"]
        party_level = options["party_level"]

        # Demo content lands in a campaign owned by the first superuser.
        owner = get_user_model().objects.filter(is_superuser=True).first()
        campaign = None
        if owner:
            campaign, _ = Campaign.objects.get_or_create(
                name="Demo Campaign",
                defaults={"owner": owner, "description": "Generated demo content"},
            )

        self.stdout.write(f"Generating location for: {concept!r} ...")
        gen_location = engine.generate_location(concept)
        location = orchestrator.save_location(
            gen_location, party_level=party_level, campaign=campaign
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

            named_slots = [
                s for s in gen_faction.hierarchy if s.tier is not RankTier.MOB
            ]
            mob_slots = [s for s in gen_faction.hierarchy if s.tier is RankTier.MOB]

            try:
                for gen_character in engine.fill_roster(
                    gen_location, gen_faction, named_slots
                ):
                    character = orchestrator.save_character(faction, gen_character)
                    line = f"    {character.rank_title}: {character.name}"
                    if not options["skip_sheets"]:
                        sheet = engine.generate_combat_sheet(
                            gen_character,
                            gen_faction,
                            party_level=party_level,
                            slot=engine.slot_for_title(
                                gen_faction, gen_character.rank_title
                            ),
                        )
                        orchestrator.save_combat_sheet(character, sheet)
                        line += f" [{sheet.profession}, HP {sheet.stats.hp}, AC {sheet.stats.ac}"
                        if sheet.legendary_actions:
                            line += f", LEGENDARY x{len(sheet.legendary_actions)}"
                        line += "]"
                    self.stdout.write(line)

                for archetype in engine.generate_mob_archetypes(
                    gen_location, gen_faction, mob_slots
                ):
                    character = orchestrator.save_mob_archetype(faction, archetype)
                    copies = ", ".join(n["name"] for n in character.instances)
                    line = f"    {character.rank_title} (mob x{len(character.instances)}): {character.name} [{copies}]"
                    if not options["skip_sheets"]:
                        sheet = engine.generate_combat_sheet(
                            archetype,
                            gen_faction,
                            party_level=party_level,
                            slot=engine.slot_for_title(
                                gen_faction, archetype.rank_title
                            ),
                        )
                        orchestrator.save_combat_sheet(character, sheet)
                    self.stdout.write(line)
            except Exception as exc:  # keep other factions alive per failure policy
                self.stderr.write(
                    self.style.ERROR(
                        f"  Roster for {faction.name} failed ({exc}); "
                        "faction kept, characters can be regenerated later."
                    )
                )

        self.stdout.write(self.style.SUCCESS(f"Done. Location #{location.pk} is ready."))
