import numpy as np
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from pathlib import Path

# Charger le DEM corrigé
with rasterio.open('data/processed/dem_abidjan.tif') as src:
    dem = src.read(1).astype(float)
    nodata = src.nodata
    if nodata:
        dem[dem == nodata] = np.nan
    dem_meta = src.meta.copy()

# Seuils adaptés au relief d'Abidjan
SEUIL_HAUT = 10   # < 10m  : haut risque
SEUIL_MOYEN = 25   # 10-25m : risque modéré
SEUIL_FAIBLE = 50   # 25-50m : faible risque

# Carte de risque
risk_map = np.zeros_like(dem)
risk_map[dem <= SEUIL_HAUT] = 3
risk_map[(dem > SEUIL_HAUT) & (dem <= SEUIL_MOYEN)] = 2
risk_map[(dem > SEUIL_MOYEN) & (dem <= SEUIL_FAIBLE)] = 1
risk_map[np.isnan(dem)] = 0

# Statistiques
total = np.sum(~np.isnan(dem))
print("── Zones de risque ──")
print(
    f"🔴 Haut risque  (< {SEUIL_HAUT}m)     : {np.sum(risk_map == 3):,} px ({100*np.sum(risk_map == 3)/total:.1f}%)")
print(f"🟠 Modéré ({SEUIL_HAUT}-{SEUIL_MOYEN}m)        : {np.sum(risk_map == 2):,} px ({100*np.sum(risk_map == 2)/total:.1f}%)")
print(f"🟡 Faible ({SEUIL_MOYEN}-{SEUIL_FAIBLE}m)       : {np.sum(risk_map == 1):,} px ({100*np.sum(risk_map == 1)/total:.1f}%)")
print(f"⚪ Aucun  (> {SEUIL_FAIBLE}m)          : {np.sum(risk_map == 0):,} px ({100*np.sum(risk_map == 0)/total:.1f}%)")

# Sauvegarder
risk_meta = dem_meta.copy()
risk_meta.update({"dtype": "float32", "nodata": -1})
with rasterio.open('data/processed/flood_zones/flood_risk_map.tif', 'w', **risk_meta) as dst:
    dst.write(risk_map.astype('float32'), 1)
print("\nflood_risk_map.tif sauvegardé")

# Visualisation
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
axes[0].set_title("DEM — Relief d'Abidjan", fontsize=13, fontweight="bold")
im1 = axes[0].imshow(dem, cmap="terrain")
plt.colorbar(im1, ax=axes[0], label="Altitude (m)")

cmap = ListedColormap(["white", "yellow", "orange", "red"])
axes[1].set_title("Zones de risque d'inondation",
                  fontsize=13, fontweight="bold")
im2 = axes[1].imshow(risk_map, cmap=cmap, vmin=0, vmax=3)
cbar = plt.colorbar(im2, ax=axes[1], ticks=[0, 1, 2, 3])
cbar.set_ticklabels(["Aucun", "Faible", "Modéré", "Haut"])

plt.tight_layout()
plt.savefig("maps/static/flood_risk_abidjan.png", dpi=150, bbox_inches="tight")
plt.show()
print("Carte sauvegardée")
