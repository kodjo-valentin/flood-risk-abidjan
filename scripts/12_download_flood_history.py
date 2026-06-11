import os
import requests
from pathlib import Path

# ── Dossier de destination ──────────────────────────────────────────
OUTPUT_DIR = Path("E:/Abidjan flood risk intelligent/data/raw/flood_history")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Téléchargement données inondations historiques ──────────────────
# Source : Global Flood Database (Cloud to Street / Science)
# Couvre les événements d'inondation documentés 2000-2018

GFD_URL = "https://global-flood-database.cloudtostreet.ai/downloads"

files = [
    {
        "name": "DFO_4628_From_20100101_to_20241231.zip",
        "url": "https://floodobservatory.colorado.edu/temp/FloodArchive.xlsx",
        "dest": "flood_archive_2010_2024.xlsx",
        "description": "Archive mondiale des inondations (Dartmouth Flood Observatory)"
    }
]

# ── Alternative directe : Dartmouth Flood Observatory ───────────────
DFO_URL = "https://floodobservatory.colorado.edu/temp/FloodArchive.xlsx"

def download_flood_data():
    print("Téléchargement des données d'inondations historiques...")
    
    dest = OUTPUT_DIR / "flood_archive_global.xlsx"
    
    if dest.exists():
        print(f"  [SKIP] Fichier déjà présent")
        return
    
    try:
        print(f"  [↓] Dartmouth Flood Observatory Archive...")
        r = requests.get(DFO_URL, timeout=120, stream=True)
        r.raise_for_status()
        
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        
        print(f"  [✓] Téléchargé → {dest}")
        
    except Exception as e:
        print(f"  [✗] Erreur : {e}")
        print(f"\n  → Télécharge manuellement ici :")
        print(f"  https://floodobservatory.colorado.edu/temp/FloodArchive.xlsx")
        print(f"  Et place le fichier dans : {OUTPUT_DIR}")

if __name__ == "__main__":
    download_flood_data()
    print("\nÉtape suivante : filtrage sur la Côte d'Ivoire / Abidjan")