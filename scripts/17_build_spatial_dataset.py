import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from rasterio.transform import from_bounds
from rasterio.warp import reproject, Resampling
import geopandas as gpd
from pathlib import Path
from shapely.geometry import box, mapping, Point
import warnings
warnings.filterwarnings("ignore")

# ── Chemins ─────────────────────────────────────────────────────────
BASE      = Path("E:/Abidjan flood risk intelligent")
RAW       = BASE / "data/raw"
PROC      = BASE / "data/processed"
CHIRPS    = RAW  / "rainfall_historical"
ML_DIR    = PROC / "ml_features"
MODEL_DIR = BASE / "models"
ML_DIR.mkdir(parents=True, exist_ok=True)

# ── Grille Abidjan 1km × 1km ─────────────────────────────────────────
MINX, MINY, MAXX, MAXY = -4.20, 5.20, -3.80, 5.55
RESOLUTION = 0.01  # ~1km en degrés

# ── Fichiers raster ──────────────────────────────────────────────────
RASTERS = {
    "twi":        RAW  / "dem/TWI.tif",
    "dem":        PROC / "dem_abidjan.tif",
    "population": RAW  / "population/civ_ppp_2020.tif",
    "flood_risk": PROC / "flood_zones/flood_risk_map.tif",
    "flow_acc":   RAW  / "dem/D8_Flow_Accumulation.tif",
}

# ── 1. Créer la grille de pixels ─────────────────────────────────────
def create_grid():
    print("[1/5] Création de la grille spatiale 1km...")
    
    xs = np.arange(MINX, MAXX, RESOLUTION)
    ys = np.arange(MINY, MAXY, RESOLUTION)
    
    rows = []
    for y in ys:
        for x in xs:
            rows.append({
                "pixel_id": f"{x:.3f}_{y:.3f}",
                "lon": x + RESOLUTION/2,
                "lat": y + RESOLUTION/2,
                "geometry": box(x, y, x+RESOLUTION, y+RESOLUTION)
            })
    
    gdf = gpd.GeoDataFrame(rows, crs="EPSG:4326")
    print(f"  → {len(gdf)} pixels créés")
    return gdf

# ── 2. Extraire valeur raster pour chaque pixel ──────────────────────
def extract_raster_values(gdf, raster_path, col_name):
    print(f"  → Extraction {col_name}...")
    values = []
    
    with rasterio.open(raster_path) as src:
        for _, row in gdf.iterrows():
            try:
                geom = [mapping(row.geometry)]
                out_img, _ = mask(src, geom, crop=True, nodata=np.nan)
                data = out_img[0].astype(float)
                data = np.where(data < -9000, np.nan, data)
                val = float(np.nanmean(data))
            except:
                val = np.nan
            values.append(val)
    
    return values

# ── 3. Extraire précipitations CHIRPS par pixel ──────────────────────
def extract_chirps_per_pixel(gdf):
    print("\n[3/5] Extraction CHIRPS par pixel (patience...)")
    
    tif_files = sorted(CHIRPS.glob("chirps-v2.0.*.tif"))
    print(f"  → {len(tif_files)} fichiers CHIRPS à traiter")
    
    records = []
    
    for i, tif_path in enumerate(tif_files):
        parts = tif_path.stem.split(".")
        year  = int(parts[2])
        month = int(parts[3])
        
        if i % 12 == 0:
            print(f"  → Année {year}...")
        
        with rasterio.open(tif_path) as src:
            for _, row in gdf.iterrows():
                try:
                    geom = [mapping(row.geometry)]
                    out_img, _ = mask(src, geom, crop=True, nodata=np.nan)
                    data = out_img[0].astype(float)
                    data = np.where(data < -9000, np.nan, data)
                    rain = float(np.nanmean(data))
                except:
                    rain = np.nan
                
                records.append({
                    "pixel_id": row["pixel_id"],
                    "lon":      row["lon"],
                    "lat":      row["lat"],
                    "year":     year,
                    "month":    month,
                    "rainfall_mm": rain
                })
    
    df = pd.DataFrame(records)
    print(f"  [✓] {len(df)} lignes générées")
    return df

# ── 4. Assembler dataset spatial complet ────────────────────────────
def assemble_spatial_dataset(df_chirps, gdf_static):
    print("\n[4/5] Assemblage du dataset spatial...")
    
    # Merge avec features statiques
    df = df_chirps.merge(
        gdf_static.drop(columns=["geometry"]),
        on="pixel_id", how="left"
    )
    
    # Features temporelles
    df = df.sort_values(["pixel_id", "year", "month"]).reset_index(drop=True)
    df["rainfall_lag1"] = df.groupby("pixel_id")["rainfall_mm"].shift(1).fillna(0)
    df["rainfall_lag2"] = df.groupby("pixel_id")["rainfall_mm"].shift(2).fillna(0)
    df["rainfall_3m_cumul"] = (
        df.groupby("pixel_id")["rainfall_mm"]
        .transform(lambda x: x.rolling(3, min_periods=1).sum())
    )
    monthly_avg = df.groupby(["pixel_id", "month"])["rainfall_mm"].transform("mean")
    df["rainfall_anomaly"] = df["rainfall_mm"] - monthly_avg
    
    # Saison
    df["season_code"] = df["month"].apply(
        lambda m: 0 if m in [4,5,6] else 1 if m in [9,10] else 2
    )
    
    # Label flood_occurred basé sur le score de risque + précipitations
    # Un pixel est "inondé" si : flood_risk élevé ET précipitations fortes
    df["flood_score"] = (
        (df["flood_risk"].fillna(0) >= 2).astype(int) *
        (df["rainfall_mm"] > df["rainfall_mm"].quantile(0.75)).astype(int)
    )
    df["flood_occurred"] = df["flood_score"]
    
    print(f"  → {len(df)} lignes | {len(df.columns)} colonnes")
    print(f"  → Pixels inondés : {df['flood_occurred'].sum()} / {len(df)}")
    return df

# ── 5. Sauvegarder ──────────────────────────────────────────────────
def save_dataset(df):
    print("\n[5/5] Sauvegarde...")
    output = ML_DIR / "ml_spatial_dataset.csv"
    
    # Sauvegarder par chunks pour économiser la mémoire
    chunk_size = 50000
    for i, chunk_start in enumerate(range(0, len(df), chunk_size)):
        chunk = df.iloc[chunk_start:chunk_start+chunk_size]
        mode = "w" if i == 0 else "a"
        header = i == 0
        chunk.to_csv(output, mode=mode, header=header, index=False)
        print(f"  → Chunk {i+1} sauvegardé ({chunk_start+len(chunk)}/{len(df)})")
    
    print(f"  [✓] Dataset spatial → {output}")
    size_mb = output.stat().st_size / 1024 / 1024
    print(f"  → Taille : {size_mb:.1f} MB")

# ── MAIN ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Étape 1 : grille
    gdf = create_grid()
    
    # Étape 2 : features statiques par pixel
    print("\n[2/5] Extraction features statiques par pixel...")
    for col, path in RASTERS.items():
        gdf[col] = extract_raster_values(gdf, path, col)
    
    # Supprimer pixels sans données (mer, hors zone)
    gdf = gdf.dropna(subset=["dem"]).reset_index(drop=True)
    print(f"  [✓] {len(gdf)} pixels valides après filtrage")
    
    # Étape 3 : précipitations par pixel × mois
    df_chirps = extract_chirps_per_pixel(gdf)
    
    # Étape 4 : assemblage
    df_final = assemble_spatial_dataset(df_chirps, gdf)
    
    # Étape 5 : sauvegarde
    save_dataset(df_final)
    
    print("\nDataset spatial prêt pour entraînement !")
    print(f"   Dimensions finales : {df_final.shape}")