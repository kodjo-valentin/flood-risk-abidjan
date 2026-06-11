from shapely.geometry import box
import gzip
import shutil
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from rasterio.transform import from_bounds
from pathlib import Path
from shapely.geometry import mapping

# ── Chemins ─────────────────────────────────────────────────────────
BASE = Path("E:/Abidjan flood risk intelligent")
RAW = BASE / "data/raw"
PROC = BASE / "data/processed"
ML_DIR = PROC / "ml_features"
ML_DIR.mkdir(parents=True, exist_ok=True)

CHIRPS_DIR = RAW / "rainfall_historical"
FLOOD_FILE = RAW / "flood history/emdat_flood_cotedivoire_2010_2024.xlsx"
DEM_FILE = PROC / "dem_abidjan.tif"
TWI_FILE = RAW / "dem/TWI.tif"
POP_FILE = RAW / "population/civ_ppp_2020.tif"
ADMIN_FILE = RAW / "admin/gadm41_CIV.gpkg"

# ── Emprise Abidjan (bounding box) ──────────────────────────────────
ABIDJAN_BOUNDS = {
    "minx": -4.20, "miny": 5.20,
    "maxx": -3.80, "maxy": 5.55
}

ABIDJAN_GEOM = [mapping(box(
    ABIDJAN_BOUNDS["minx"], ABIDJAN_BOUNDS["miny"],
    ABIDJAN_BOUNDS["maxx"], ABIDJAN_BOUNDS["maxy"]
))]

# ── 1. Décompresser les fichiers CHIRPS ──────────────────────────────


def decompress_chirps():
    print("\n[1/4] Décompression des fichiers CHIRPS...")
    gz_files = list(CHIRPS_DIR.glob("*.tif.gz"))
    print(f"  → {len(gz_files)} fichiers à décompresser")

    for gz_path in gz_files:
        tif_path = CHIRPS_DIR / gz_path.stem  # retire le .gz
        if tif_path.exists():
            continue
        with gzip.open(gz_path, 'rb') as f_in:
            with open(tif_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    print(f"  [✓] Décompression terminée")

# ── 2. Extraire précipitations mensuelles sur Abidjan ────────────────


def extract_rainfall():
    print("\n[2/4] Extraction des précipitations sur Abidjan...")
    tif_files = sorted(CHIRPS_DIR.glob("chirps-v2.0.*.tif"))

    records = []
    for tif_path in tif_files:
        # Extraire année et mois depuis le nom du fichier
        parts = tif_path.stem.split(".")  # chirps-v2 / 0 / 2010 / 01
        year = int(parts[2])
        month = int(parts[3])

        try:
            with rasterio.open(tif_path) as src:
                out_image, _ = mask(src, ABIDJAN_GEOM, crop=True)
                data = out_image[0]
                data = np.where(data < 0, np.nan, data)  # nodata → NaN

                records.append({
                    "year":        year,
                    "month":       month,
                    "rainfall_mm": float(np.nanmean(data)),
                    "rainfall_max": float(np.nanmax(data)),
                    "rainfall_sum": float(np.nansum(data))
                })
        except Exception as e:
            print(f"  [✗] {tif_path.name} : {e}")

    df = pd.DataFrame(records)
    print(f"  [✓] {len(df)} entrées extraites")
    return df

# ── 3. Préparer les données d'inondations EM-DAT ────────────────────


def prepare_flood_labels():
    print("\n[3/4] Préparation des labels d'inondation (EM-DAT)...")

    # Lire sans skiprows pour détecter la vraie structure
    df_raw = pd.read_excel(FLOOD_FILE, header=None)

    # Trouver la ligne qui contient les vrais en-têtes
    header_row = None
    for i, row in df_raw.iterrows():
        row_str = " ".join([str(v).lower() for v in row.values])
        if "year" in row_str and "country" in row_str:
            header_row = i
            break

    if header_row is None:
        # Afficher les 10 premières lignes pour diagnostic
        print("  Structure du fichier :")
        print(df_raw.head(10).to_string())
        raise ValueError("En-tête introuvable — voir structure ci-dessus")

    print(f"  → En-tête trouvé à la ligne {header_row}")
    df = pd.read_excel(FLOOD_FILE, skiprows=header_row)
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")
    print(f"  Colonnes : {list(df.columns)}")

    # Filtrer Côte d'Ivoire
    country_col = next((c for c in df.columns if "country" in c), None)
    if country_col:
        df = df[df[country_col].str.contains("Ivoire", na=False, case=False)]

    # Trouver colonnes year et month
    year_col = next((c for c in df.columns if "year" in c), None)
    month_col = next((c for c in df.columns if "month" in c), None)
    death_col = next((c for c in df.columns if "death" in c), None)
    aff_col = next((c for c in df.columns if "affected" in c), None)

    print(f"  → year={year_col}, month={month_col}, deaths={death_col}")

    df = df.dropna(subset=[year_col])
    df = df.rename(columns={
        year_col:  "year",
        month_col: "month" if month_col else "month"
    })

    if "month" not in df.columns:
        df["month"] = 1  # valeur par défaut si absent

    df["year"] = df["year"].astype(int)
    df["month"] = pd.to_numeric(
        df["month"], errors="coerce").fillna(1).astype(int)
    df["flood_occurred"] = 1

    print(f"  [✓] {len(df)} événements d'inondation en Côte d'Ivoire")
    return df
# ── 4. Assembler le dataset ML final ────────────────────────────────


def assemble_dataset(df_rain, df_floods):
    print("\n[4/4] Assemblage du dataset ML...")

    # Merge sur année + mois
    df = df_rain.merge(df_floods, on=["year", "month"], how="left")
    df["flood_occurred"] = df["flood_occurred"].fillna(0).astype(int)

    # Features temporelles
    df["season"] = df["month"].apply(
        lambda m: "grande_saison_pluies" if m in [4, 5, 6]
        else "petite_saison_pluies" if m in [9, 10]
        else "saison_seche"
    )
    df["season_code"] = df["season"].astype("category").cat.codes

    # Sauvegarder
    output = ML_DIR / "ml_dataset.csv"
    df.to_csv(output, index=False)

    print(f"  [✓] Dataset sauvegardé → {output}")
    print(f"  → {len(df)} lignes | {len(df.columns)} colonnes")
    print(f"  → Inondations : {df['flood_occurred'].sum()} mois sur {len(df)}")
    print(f"\n  Aperçu :")
    print(df.head())
    return df


# ── MAIN ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    decompress_chirps()
    df_rain = extract_rainfall()
    df_floods = prepare_flood_labels()
    df_final = assemble_dataset(df_rain, df_floods)
    print("\nDonnées ML prêtes !")
