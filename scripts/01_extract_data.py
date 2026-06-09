import tarfile
import zipfile
import gzip
import shutil
import os
from pathlib import Path

# ── Dossiers ────────────────────────────────────────────────
DEM_DIR = Path("data/raw/dem")
RAINFALL_DIR = Path("data/raw/rainfall")

# ── 1. Extraire les fichiers DEM (.tar.gz) ───────────────────
print("Extraction des fichiers DEM...")

for file in DEM_DIR.glob("*.tar.gz"):
    print(f"  → Extraction de {file.name}")
    with tarfile.open(file, "r:gz") as tar:
        tar.extractall(path=DEM_DIR)
    print(f"{file.name} extrait")

# ── 2. Extraire streams.zip ──────────────────────────────────
streams_zip = DEM_DIR / "streams.zip"
if streams_zip.exists():
    print("\nExtraction de streams.zip...")
    with zipfile.ZipFile(streams_zip, "r") as z:
        z.extractall(path=DEM_DIR)
    print("streams.zip extrait")

# ── 3. Extraire les fichiers pluies (.tif.gz) ────────────────
print("\nExtraction des fichiers pluies...")

for file in RAINFALL_DIR.glob("*.tif.gz"):
    output_file = RAINFALL_DIR / file.stem  # retire le .gz
    print(f"  → Extraction de {file.name}")
    with gzip.open(file, "rb") as f_in:
        with open(output_file, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
    print(f"{output_file.name} extrait")

print("\nToutes les extractions sont terminées !")
print("\nContenu du dossier DEM :")
for f in sorted(DEM_DIR.iterdir()):
    print(f"  {f.name}")

print("\nContenu du dossier Rainfall :")
for f in sorted(RAINFALL_DIR.iterdir()):
    print(f"  {f.name}")