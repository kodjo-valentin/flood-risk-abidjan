import numpy as np
import rasterio
from rasterio.enums import Resampling
import matplotlib.pyplot as plt
from pathlib import Path

# ── Dossiers ────────────────────────────────────────────────
PROCESSED_DIR = Path("data/processed")
OUTPUT_DIR = Path("data/processed/exposed_pop")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── 1. Charger la carte de risque ───────────────────────────
print("Chargement de la carte de risque...")
with rasterio.open(PROCESSED_DIR / "flood_zones/flood_risk_map.tif") as src:
    risk_map = src.read(1).astype(float)
    risk_meta = src.meta.copy()
    risk_transform = src.transform
    risk_crs = src.crs
    risk_shape = src.shape

# ── 2. Charger et rééchantillonner la population ────────────
print("Chargement de la population...")
with rasterio.open(PROCESSED_DIR / "population_abidjan.tif") as src:
    pop = src.read(
        1,
        out_shape=risk_shape,
        resampling=Resampling.bilinear
    ).astype(float)
    nodata = src.nodata
    if nodata:
        pop[pop == nodata] = 0
    pop[pop < 0] = 0

print(f"✅ Population totale Abidjan : {np.nansum(pop):,.0f} habitants")

# ── 3. Calculer la population exposée par zone ──────────────
print("\nCalcul de la population exposée...")

pop_haut   = np.sum(pop[risk_map == 3])
pop_moyen  = np.sum(pop[risk_map == 2])
pop_faible = np.sum(pop[risk_map == 1])
pop_aucun  = np.sum(pop[risk_map == 0])
pop_total  = pop_haut + pop_moyen + pop_faible + pop_aucun

print("\n── Population exposée par zone de risque ──")
print(f"🔴 Haut risque   : {pop_haut:>12,.0f} hab. ({100*pop_haut/pop_total:.1f}%)")
print(f"🟠 Risque modéré : {pop_moyen:>12,.0f} hab. ({100*pop_moyen/pop_total:.1f}%)")
print(f"🟡 Faible risque : {pop_faible:>12,.0f} hab. ({100*pop_faible/pop_total:.1f}%)")
print(f"⚪ Aucun risque  : {pop_aucun:>12,.0f} hab. ({100*pop_aucun/pop_total:.1f}%)")
print(f"\n👥 Total         : {pop_total:>12,.0f} hab.")

# ── 4. Sauvegarder population exposée (haut + modéré) ───────
exposed = np.where(risk_map >= 2, pop, 0)
exp_meta = risk_meta.copy()
exp_meta.update({"dtype": "float32", "nodata": -1})

with rasterio.open(OUTPUT_DIR / "exposed_population.tif", "w", **exp_meta) as dst:
    dst.write(exposed.astype("float32"), 1)
print("\n✅ exposed_population.tif sauvegardé")

# ── 5. Visualisation améliorée ───────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 6))

# Population totale
axes[0].set_title("Population d'Abidjan (2020)", fontsize=13, fontweight="bold")
im1 = axes[0].imshow(np.sqrt(pop), cmap="YlOrRd")
plt.colorbar(im1, ax=axes[0], label="Habitants / pixel (√)")

# Population exposée
axes[1].set_title("Population exposée aux inondations", fontsize=13, fontweight="bold")
im2 = axes[1].imshow(np.sqrt(exposed), cmap="Reds")
plt.colorbar(im2, ax=axes[1], label="Habitants / pixel (√)")

plt.tight_layout()
plt.savefig("maps/static/population_exposure.png", dpi=150, bbox_inches="tight")
plt.show()
print("Carte sauvegardée")