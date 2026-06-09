import osmnx as ox
import geopandas as gpd

# ── 1. Réseau routier d'Abidjan ──────────────────────────────
print("Téléchargement du réseau routier...")
G = ox.graph_from_place("Abidjan, Côte d'Ivoire", network_type="drive")
ox.save_graphml(G, filepath="data/raw/osm/abidjan_roads.graphml")
print("Réseau routier sauvegardé")

# ── 2. Infrastructures critiques (hôpitaux, écoles, etc.) ────
print("Téléchargement des POIs critiques...")
tags = {
    "amenity": ["hospital", "school", "clinic", "fire_station", "police"]
}
pois = ox.features_from_place("Abidjan, Côte d'Ivoire", tags=tags)
pois.to_file("data/raw/osm/abidjan_pois.geojson", driver="GeoJSON")
print(" POIs sauvegardés")

print("\nTéléchargement OSM terminé !")