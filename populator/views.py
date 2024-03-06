from django.shortcuts import render


def index(request):
    return render(request, "populator/index.html")


def populator(request):
    return render(request, "populator/populator.html")


def demo(request):
    return render(request, "populator/demo/demo_index.html")


def demo_location(request):
    demo_locations = [
            {
        "name": "Langfeyglade",
        "location_type": "Fairy Kingdom in Strife",
        "description": "A once serene and hidden kingdom, known for its lush, enchanted forests and mystical creatures, is now on the brink of civil unrest. Ancient magic wanes, and factions vie for control over the remaining sources of magical power.",
        },
            {
        "name": "Coralight",
        "location_type": "Underwater City",
        "description": "A breathtaking city beneath the waves, built from living coral and bioluminescent plants, is threatened by external invasions and internal decay. Its inhabitants, a mix of merfolk, sentient sea creatures, and adapted surface dwellers, face a future uncertain.",
        },
            {
        "name": "Aetheria's Reach",
        "location_type": "Skyborne Archipelago",
        "description": "A series of floating islands above a seemingly endless void, connected by bridges of light and ancient magic. The islands are a haven for air elementals, sky pirates, and adventurers seeking the thrill of the unknown.",
            }
    ]
    return render(request, "populator/demo/demo_location.html", {"demo_locations": demo_locations})


def demo_factions(request):
    demo_factions = [
            {
        "name": "The Thornheart Syndicate",
        "faction_type": " Thieves' Guild",
        "description": "An elusive and ruthless band of thieves and assassins who seek to exploit the kingdom's strife for their gain. They thrive in chaos, using the cover of unrest to steal magical artifacts and eliminate those who stand in their way.",
        },
            {
        "name": "The Duskwood Enclave",
        "faction_type": "Dark Druids",
        "description": "A faction of druids who have turned to dark magic, believing that the only way to restore the kingdom is through purging it with fire and shadow. They manipulate the natural order, summoning dangerous creatures and blighting the land.",
        },
            {
        "name": "The Silent Crown",
        "faction_type": "Secret Society",
        "description": "A cabal of nobles and mages who conspire to overthrow the current monarchy. Using political manipulation and dark magic, they aim to place a puppet ruler on the throne, one who will serve their interests and grant them unfettered access to the kingdom's ancient magics.",
        },
            {
        "name": "The Gilded Merchants",
        "faction_type": "Trade Consortium",
        "description": "A powerful coalition of fairy merchants who control much of the kingdom's commerce. While primarily interested in profit, their influence over trade routes and supplies makes them a powerful entity that can sway the tide of conflict with their decisions.",
        },
            {
        "name": "The Twilight Harbingers",
        "faction_type": "Mystic Seers",
        "description": "A group of oracles and seers who claim neutrality, offering their prophetic services to all. They believe in the inevitability of fate and see the strife as a necessary part of the kingdom's evolution, guiding those who seek their wisdom.",
        },
            {
        "name": "The Woven Kin",
        "faction_type": "Artisans Guild",
        "description": "A collective of craftsmen, artists, and enchanters dedicated to preserving the kingdom's cultural heritage. They remain neutral, focusing on their craft and the belief that beauty and art can heal the rifts tearing their society apart.",
        },
            {
        "name": "The Verdant Shield",
        "faction_type": "Rangers",
        "description": "A band of rangers and beastmasters who protect the kingdom's borders and wildlands. They are committed to defending the realm from external threats and aiding those displaced or harmed by the conflict.",
        },
            {
        "name": "The Luminous Covenant",
        "faction_type": "Paladin Order",
        "description": "A holy order of paladins and light-wielders who fight to preserve peace and justice in the kingdom. They offer sanctuary to refugees, battle dark forces, and work to mend the rifts between conflicting factions.",
        },
            {
        "name": "The Crystalborne Alliance",
        "faction_type": "Mage Circle",
        "description": "A circle of mages specializing in healing and protective magics. They focus on aiding the wounded and the weak, repairing damaged lands, and seeking peaceful resolutions to conflict. Their magic is a beacon of hope for many in these dark times.",
        }
    ]
    return render(request, "populator/demo/demo_factions.html", {"demo_factions": demo_factions})


def demo_characters(request):
    return render(request, "populator/demo/demo_characters.html")


def demo_summary(request):
    return render(request, "populator/demo/demo_summary.html")
