import json
import geopandas as gpd
from pathlib import Path

web_dir = Path('web/assets/data')

print("Simplification de flood_risk.geojson...")
gdf = gpd.read_file(web_dir / 'flood_risk.geojson')
print(f"Avant : {len(gdf)} features")

# Simplifier la géométrie (tolérance en degrés)
gdf['geometry'] = gdf.geometry.simplify(tolerance=0.001, preserve_topology=True)

# Supprimer les géométries vides
gdf = gdf[~gdf.geometry.is_empty]
gdf = gdf[gdf.geometry.notna()]

print(f"Après : {len(gdf)} features")

# Sauvegarder
gdf.to_file(web_dir / 'flood_risk_simplified.geojson', driver='GeoJSON')

# Convertir en JS
with open(web_dir / 'flood_risk_simplified.geojson') as f:
    data = json.load(f)

js = 'const DATA_FLOOD_RISK = ' + json.dumps(data) + ';'
with open(web_dir / 'flood_risk.js', 'w') as f:
    f.write(js)

print(f"flood_risk.js simplifié — {len(data['features'])} features")