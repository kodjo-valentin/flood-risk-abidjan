import numpy as np
import rasterio
from rasterio.features import shapes
import geopandas as gpd
from shapely.geometry import shape
import json
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

PROCESSED_DIR = Path("data/processed")
WEB_DIR = Path("web/assets/data")
WEB_DIR.mkdir(parents=True, exist_ok=True)

# ── 1. Convertir la carte de risque en GeoJSON ───────────────
print("Conversion de la carte de risque...")
with rasterio.open(PROCESSED_DIR / "flood_zones/flood_risk_map.tif") as src:
    image = src.read(1).astype("float32")
    transform = src.transform
    crs = src.crs

# Vectoriser chaque zone de risque
features = []
for level, label, color in [
    (3, "Haut risque", "#d73027"),
    (2, "Risque modéré", "#fc8d59"),
    (1, "Faible risque", "#fee08b")
]:
    mask = (image == level).astype("uint8")
    for geom, val in shapes(mask, transform=transform):
        if val == 1:
            features.append({
                "type": "Feature",
                "geometry": geom,
                "properties": {
                    "risk_level": level,
                    "risk_label": label,
                    "color": color
                }
            })

geojson_risk = {"type": "FeatureCollection", "features": features}
with open(WEB_DIR / "flood_risk.geojson", "w") as f:
    json.dump(geojson_risk, f)
print(f"flood_risk.geojson — {len(features)} zones")

# ── 2. Exporter les infrastructures critiques ────────────────
print("Export des infrastructures critiques...")
critiques = gpd.read_file(
    PROCESSED_DIR / "risk_index/critiques_avec_risque.geojson"
)
critiques = critiques.to_crs("EPSG:4326")

# Garder uniquement les colonnes utiles
cols_utiles = ["geometry", "name", "amenity", "risk_level", "risk_label"]
cols_presentes = [c for c in cols_utiles if c in critiques.columns]
critiques = critiques[cols_presentes]

# Convertir en points si polygones
critiques["geometry"] = critiques["geometry"].centroid
critiques.to_file(WEB_DIR / "critiques.geojson", driver="GeoJSON")
print(f"critiques.geojson — {len(critiques)} infrastructures")

# ── 3. Exporter les équipements ──────────────────────────────
print("Export des équipements...")
equipements = gpd.read_file(
    PROCESSED_DIR / "risk_index/equipements_avec_risque.geojson"
)
equipements = equipements.to_crs("EPSG:4326")
cols_utiles = ["geometry", "name", "amenity", "leisure", "shop", 
               "risk_level", "risk_label"]
cols_presentes = [c for c in cols_utiles if c in equipements.columns]
equipements = equipements[cols_presentes]
equipements["geometry"] = equipements["geometry"].centroid
equipements.to_file(WEB_DIR / "equipements.geojson", driver="GeoJSON")
print(f"equipements.geojson — {len(equipements)} équipements")

# ── 4. Résumé statistique pour le dashboard ─────────────────
print("Génération des statistiques...")
stats = {
    "population": {
        "total": 46487336,
        "haut_risque": 14031523,
        "moyen_risque": 3943139,
        "faible_risque": 8729421
    },
    "infrastructures": {
        "total": 3688,
        "haut_risque": 689,
        "moyen_risque": 180,
        "faible_risque": 811
    },
    "equipements": {
        "total": 1250,
        "haut_risque": 286,
        "moyen_risque": 81,
        "faible_risque": 262
    },
    "batiments": {
        "total": 392618,
        "haut_risque": 67245,
        "moyen_risque": 27193,
        "faible_risque": 76550
    }
}

with open(WEB_DIR / "stats.json", "w") as f:
    json.dump(stats, f, indent=2)
print("stats.json sauvegardé")

print("\nTous les fichiers web sont prêts dans web/assets/data/")