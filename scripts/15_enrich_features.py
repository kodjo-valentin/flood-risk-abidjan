import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
from pathlib import Path
from shapely.geometry import box, mapping

# ── Chemins ─────────────────────────────────────────────────────────
BASE     = Path("E:/Abidjan flood risk intelligent")
RAW      = BASE / "data/raw"
PROC     = BASE / "data/processed"
ML_DIR   = PROC / "ml_features"
MODEL_DIR = BASE / "models"

# ── Emprise Abidjan ──────────────────────────────────────────────────
ABIDJAN_GEOM = [mapping(box(-4.20, 5.20, -3.80, 5.55))]

# ── Fichiers raster disponibles ──────────────────────────────────────
RASTERS = {
    "twi_mean":        RAW  / "dem/TWI.tif",
    "dem_mean":        PROC / "dem_abidjan.tif",
    "pop_density":     RAW  / "population/civ_ppp_2020.tif",
    "flood_risk_mean": PROC / "flood_zones/flood_risk_map.tif",
    "flow_acc_mean":   RAW  / "dem/D8_Flow_Accumulation.tif",
}

# ── Extraire statistiques zonales depuis un raster ───────────────────
def extract_stats(raster_path, label):
    try:
        with rasterio.open(raster_path) as src:
            out_image, _ = mask(src, ABIDJAN_GEOM, crop=True)
            data = out_image[0].astype(float)
            nodata = src.nodata
            if nodata is not None:
                data = np.where(data == nodata, np.nan, data)
            data = np.where(data < -9000, np.nan, data)

            return {
                f"{label}_mean": float(np.nanmean(data)),
                f"{label}_max":  float(np.nanmax(data)),
                f"{label}_std":  float(np.nanstd(data)),
            }
    except Exception as e:
        print(f"  [✗] {label} : {e}")
        return {f"{label}_mean": np.nan,
                f"{label}_max":  np.nan,
                f"{label}_std":  np.nan}

# ── MAIN ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[1/3] Extraction des features spatiales...")

    spatial_stats = {}
    for label, path in RASTERS.items():
        print(f"  → {label}")
        stats = extract_stats(path, label)
        spatial_stats.update(stats)
        for k, v in stats.items():
            print(f"     {k} = {v:.4f}")

    print("\n[2/3] Chargement du dataset ML existant...")
    df = pd.read_csv(ML_DIR / "ml_dataset.csv")
    print(f"  → {len(df)} lignes | {len(df.columns)} colonnes")

    # Ajouter les features spatiales (constantes pour toutes les lignes
    # car on travaille sur une zone fixe — Abidjan)
    for col, val in spatial_stats.items():
        df[col] = val

    # ── Features temporelles enrichies ──────────────────────────────
    # Précipitations du mois précédent (lag)
    df = df.sort_values(["year", "month"]).reset_index(drop=True)
    df["rainfall_lag1"] = df["rainfall_mm"].shift(1).fillna(0)
    df["rainfall_lag2"] = df["rainfall_mm"].shift(2).fillna(0)
    df["rainfall_lag3"] = df["rainfall_mm"].shift(3).fillna(0)

    # Cumul sur 3 mois glissants
    df["rainfall_3m_cumul"] = (
        df["rainfall_mm"].rolling(window=3, min_periods=1).sum()
    )

    # Anomalie par rapport à la moyenne mensuelle historique
    monthly_avg = df.groupby("month")["rainfall_mm"].transform("mean")
    df["rainfall_anomaly"] = df["rainfall_mm"] - monthly_avg

    print("\n[3/3] Sauvegarde du dataset enrichi...")
    output = ML_DIR / "ml_dataset_enriched.csv"
    df.to_csv(output, index=False)

    # Afficher les nouvelles colonnes
    new_cols = list(spatial_stats.keys()) + [
        "rainfall_lag1", "rainfall_lag2", "rainfall_lag3",
        "rainfall_3m_cumul", "rainfall_anomaly"
    ]
    print(f"  [✓] {len(new_cols)} nouvelles features ajoutées :")
    for c in new_cols:
        print(f"     + {c}")

    print(f"\n  Dataset enrichi → {output}")
    print(f"  Dimensions : {df.shape[0]} lignes | {df.shape[1]} colonnes")
    print("\nFeatures enrichies — prêt pour ré-entraînement !")