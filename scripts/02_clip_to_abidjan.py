import geopandas as gpd
import rasterio
from rasterio.mask import mask
from pathlib import Path

# ── Dossiers ────────────────────────────────────────────────
ADMIN_DIR = Path("data/raw/admin")
DEM_DIR = Path("data/raw/dem")
RAINFALL_DIR = Path("data/raw/rainfall")
POP_DIR = Path("data/raw/population")
OUTPUT_DIR = Path("data/processed")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 1. Charger les limites d'Abidjan (GADM niveau 2) ────────
print("Chargement des limites administratives...")
gadm = gpd.read_file(list(ADMIN_DIR.glob("*.gpkg"))[0], layer="ADM_ADM_2")
abidjan = gadm[gadm["NAME_2"].str.contains("Abidjan", case=False, na=False)]

if abidjan.empty:
    abidjan = gadm[gadm["NAME_1"].str.contains("Abidjan", case=False, na=False)]

print(f"Zone Abidjan chargée : {len(abidjan)} entités")
abidjan = abidjan.to_crs("EPSG:4326")
geometry = abidjan.geometry.values

# ── Fonction de découpage ────────────────────────────────────
def clip_raster(input_path, output_path, geometry):
    with rasterio.open(input_path) as src:
        out_image, out_transform = mask(src, geometry, crop=True)
        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform
        })
        with rasterio.open(output_path, "w", **out_meta) as dest:
            dest.write(out_image)
    print(f"{output_path.name} sauvegardé")

# ── 2. Découper le DEM ───────────────────────────────────────
print("\nDécoupage du DEM...")
dem_files = list(DEM_DIR.glob("*.tif"))
if dem_files:
    clip_raster(dem_files[0], OUTPUT_DIR / "dem_abidjan.tif", geometry)

# ── 3. Découper la population ────────────────────────────────
print("\nDécoupage de la population...")
pop_files = list(POP_DIR.glob("*2020*.tif"))
if pop_files:
    clip_raster(pop_files[0], OUTPUT_DIR / "population_abidjan.tif", geometry)

# ── 4. Découper les données pluies ───────────────────────────
print("\nDécoupage des données pluies...")
rainfall_dir_out = OUTPUT_DIR / "rainfall"
rainfall_dir_out.mkdir(exist_ok=True)

for tif in RAINFALL_DIR.glob("*.tif"):
    clip_raster(tif, rainfall_dir_out / f"clipped_{tif.name}", geometry)

print("\nTous les découpages sont terminés !")