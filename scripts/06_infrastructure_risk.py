import geopandas as gpd
import rasterio
from rasterio.sample import sample_gen
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

# ── Dossiers ────────────────────────────────────────────────
OSM_DIR = Path("data/raw/osm")
PROCESSED_DIR = Path("data/processed")
OUTPUT_DIR = Path("data/processed/risk_index")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 1. Charger la carte de risque ───────────────────────────
print("Chargement de la carte de risque...")
risk_src = rasterio.open(PROCESSED_DIR / "flood_zones/flood_risk_map.tif")

def get_risk_value(gdf, risk_src):
    """Extrait le niveau de risque pour chaque point/polygone"""
    gdf = gdf.to_crs(risk_src.crs)
    # Utiliser le centroïde pour les polygones
    coords = [(geom.centroid.x, geom.centroid.y) 
              if geom.geom_type != 'Point' 
              else (geom.x, geom.y) 
              for geom in gdf.geometry]
    risk_values = [val[0] for val in risk_src.sample(coords)]
    return risk_values

# ── 2. Infrastructures critiques ────────────────────────────
print("\nAnalyse des infrastructures critiques...")
critiques = gpd.read_file(OSM_DIR / "abidjan_critiques.geojson")
critiques["risk_level"] = get_risk_value(critiques, risk_src)

risk_labels = {0: "Aucun", 1: "Faible", 2: "Modéré", 3: "Haut"}
critiques["risk_label"] = critiques["risk_level"].map(risk_labels)

print("\n── Infrastructures critiques par zone de risque ──")
for level, label in [(3,"🔴 Haut"), (2,"🟠 Modéré"), (1,"🟡 Faible"), (0,"⚪ Aucun")]:
    count = (critiques["risk_level"] == level).sum()
    pct = 100 * count / len(critiques)
    print(f"  {label:15} : {count:4d} ({pct:.1f}%)")

critiques.to_file(OUTPUT_DIR / "critiques_avec_risque.geojson", driver="GeoJSON")
print("critiques_avec_risque.geojson sauvegardé")

# ── 3. Équipements publics ───────────────────────────────────
print("\nAnalyse des équipements publics...")
equipements = gpd.read_file(OSM_DIR / "abidjan_equipements.geojson")
equipements["risk_level"] = get_risk_value(equipements, risk_src)
equipements["risk_label"] = equipements["risk_level"].map(risk_labels)

print("\n── Équipements publics par zone de risque ──")
for level, label in [(3,"🔴 Haut"), (2,"🟠 Modéré"), (1,"🟡 Faible"), (0,"⚪ Aucun")]:
    count = (equipements["risk_level"] == level).sum()
    pct = 100 * count / len(equipements)
    print(f"  {label:15} : {count:4d} ({pct:.1f}%)")

equipements.to_file(OUTPUT_DIR / "equipements_avec_risque.geojson", driver="GeoJSON")
print("equipements_avec_risque.geojson sauvegardé")

# ── 4. Bâtiments ─────────────────────────────────────────────
print("\nAnalyse des bâtiments...")
batiments = gpd.read_file(OSM_DIR / "abidjan_batiments.geojson")
batiments["risk_level"] = get_risk_value(batiments, risk_src)
batiments["risk_label"] = batiments["risk_level"].map(risk_labels)

print("\n── Bâtiments par zone de risque ──")
for level, label in [(3,"🔴 Haut"), (2,"🟠 Modéré"), (1,"🟡 Faible"), (0,"⚪ Aucun")]:
    count = (batiments["risk_level"] == level).sum()
    pct = 100 * count / len(batiments)
    print(f"  {label:15} : {count:5d} ({pct:.1f}%)")

batiments.to_file(OUTPUT_DIR / "batiments_avec_risque.geojson", driver="GeoJSON")
print("batiments_avec_risque.geojson sauvegardé")

# ── 5. Visualisation ─────────────────────────────────────────
print("\nGénération du graphique...")
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
colors = ["#d73027", "#fc8d59", "#fee08b", "#d9d9d9"]
labels = ["Haut", "Modéré", "Faible", "Aucun"]

for ax, gdf, titre in zip(axes,
                           [critiques, equipements, batiments],
                           ["Infrastructures critiques", 
                            "Équipements publics", 
                            "Bâtiments"]):
    counts = [(gdf["risk_level"] == lvl).sum() for lvl in [3, 2, 1, 0]]
    ax.bar(labels, counts, color=colors)
    ax.set_title(titre, fontsize=12, fontweight="bold")
    ax.set_ylabel("Nombre")
    for i, v in enumerate(counts):
        ax.text(i, v + 5, str(v), ha="center", fontsize=9)

plt.tight_layout()
plt.savefig("maps/static/infrastructure_risk.png", dpi=150, bbox_inches="tight")
plt.show()
print("Graphique sauvegardé")

risk_src.close()