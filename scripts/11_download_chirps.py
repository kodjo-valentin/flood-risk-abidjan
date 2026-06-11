import os
import requests
from pathlib import Path

# ── Dossier de destination ──────────────────────────────────────────
OUTPUT_DIR = Path("E:/Abidjan flood risk intelligent/data/raw/rainfall_historical")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Zone Abidjan (bounding box) ─────────────────────────────────────
# CHIRPS fournit des fichiers globaux qu'on télécharge directement
BASE_URL = "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs"

# ── Années et mois à télécharger ────────────────────────────────────
YEARS = range(2010, 2025)  # 2010 → 2024
MONTHS = range(1, 13)      # janvier → décembre

# ── Téléchargement ──────────────────────────────────────────────────
def download_chirps():
    total = len(list(YEARS)) * 12
    count = 0
    errors = []

    for year in YEARS:
        for month in MONTHS:
            filename = f"chirps-v2.0.{year}.{month:02d}.tif.gz"
            url = f"{BASE_URL}/{filename}"
            dest = OUTPUT_DIR / filename

            # Sauter si déjà téléchargé
            if dest.exists():
                print(f"  [SKIP] {filename} déjà présent")
                count += 1
                continue

            try:
                print(f"  [↓] {filename} ({count+1}/{total})")
                r = requests.get(url, timeout=60, stream=True)
                r.raise_for_status()

                with open(dest, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

                print(f"  [✓] Téléchargé")
                count += 1

            except Exception as e:
                print(f"  [✗] Erreur : {e}")
                errors.append(filename)

    print(f"\n{'='*50}")
    print(f"Terminé : {count - len(errors)}/{total} fichiers téléchargés")
    if errors:
        print(f"Échecs ({len(errors)}) : {errors}")

if __name__ == "__main__":
    download_chirps()