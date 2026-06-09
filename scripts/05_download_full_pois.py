import osmnx as ox
import geopandas as gpd
from pathlib import Path

OUTPUT_DIR = Path("data/raw/osm")

# ── 1. Infrastructures critiques ────────────────────────────
print("Téléchargement des infrastructures critiques...")
tags_critiques = {
    "amenity": [
        "hospital", "clinic", "health_post",
        "school", "university", "college",
        "fire_station", "police",
        "pharmacy", "place_of_worship"
    ]
}
critiques = ox.features_from_place("Abidjan, Côte d'Ivoire", tags=tags_critiques)
critiques.to_file(OUTPUT_DIR / "abidjan_critiques.geojson", driver="GeoJSON")
print(f"{len(critiques)} infrastructures critiques sauvegardées")

# ── 2. Équipements publics ───────────────────────────────────
print("\nTéléchargement des équipements publics...")
tags_equipements = {
    "amenity": ["marketplace", "bus_station", "fuel"],
    "leisure": ["park", "playground", "sports_centre"],
    "shop": ["supermarket", "mall"]
}
equipements = ox.features_from_place("Abidjan, Côte d'Ivoire", tags=tags_equipements)
equipements.to_file(OUTPUT_DIR / "abidjan_equipements.geojson", driver="GeoJSON")
print(f"{len(equipements)} équipements sauvegardés")

# ── 3. Bâtiments (maisons + immeubles) ──────────────────────
print("\nTéléchargement des bâtiments...")
tags_batiments = {
    "building": [
        "residential", "house", "apartments",
        "commercial", "industrial", "yes"
    ]
}
batiments = ox.features_from_place("Abidjan, Côte d'Ivoire", tags=tags_batiments)
batiments.to_file(OUTPUT_DIR / "abidjan_batiments.geojson", driver="GeoJSON")
print(f"{len(batiments)} bâtiments sauvegardés")

print("\nTéléchargement complet !")