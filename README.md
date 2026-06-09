# Flood Risk Intelligence — Abidjan

> **Application géospatiale de gestion de crise · Analyse du risque d'inondation à Abidjan, Côte d'Ivoire**

[![Python](https://img.shields.io/badge/Python-3.14-blue?style=flat-square&logo=python)](https://python.org)
[![Leaflet](https://img.shields.io/badge/Leaflet.js-1.9.4-green?style=flat-square)](https://leafletjs.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Data](https://img.shields.io/badge/Data-Open%20Source-orange?style=flat-square)](https://openstreetmap.org)

---

<!-- 📸 IMAGE : Capture d'écran du hero du dashboard (section accueil avec la carte visible) -->
<!-- Chemin suggéré : docs/screenshots/hero_dashboard.png -->

---

## 🎯 Contexte & Motivation

Abidjan, capitale économique de la Côte d'Ivoire avec plus de **6 millions d'habitants**, est confrontée chaque année à des inondations dévastatrices lors des saisons des pluies (mai–juin et septembre–octobre). En **juin 2026**, des pluies torrentielles ont provoqué des inondations majeures dans plusieurs communes du District Autonome d'Abidjan, contraignant le Premier Ministre Robert Beugré Mambé à décréter des **mesures d'urgence** pour rétablir la circulation et sécuriser les populations. Des immeubles ont présenté des signes d'effondrement à Bingerville, des routes ont été coupées, et des milliers de ménages ont été sinistrés.

Face à cette réalité récurrente, les autorités et les acteurs humanitaires manquent d'outils géospatiaux précis pour **anticiper les zones à risque**, **localiser les infrastructures menacées** et **quantifier les populations exposées** avant qu'une crise ne survienne.

**Ce projet répond à ce besoin** en construisant une pipeline géospatiale complète — de la donnée satellitaire brute à un dashboard interactif — pour transformer les données en intelligence opérationnelle de gestion de crise.

---

## 📊 Résultats Clés

| Indicateur | Valeur |
|---|---|
| 🔴 Population en haut risque (< 10m d'altitude) | **14 031 523 hab. (30%)** |
| 🟠 Population en risque modéré (10–25m) | **3 943 139 hab. (8,5%)** |
| 🟡 Population en faible risque (25–50m) | **8 729 421 hab. (18,8%)** |
| 🏥 Infrastructures critiques en zone rouge | **689** (hôpitaux, écoles, commissariats) |
| 🏠 Bâtiments en haut risque | **67 245** sur 392 618 cartographiés |
| 🏪 Équipements publics menacés | **286** (marchés, gares, stations) |
| 📐 Résolution DEM utilisée | **30m (NASA SRTM GL1)** |
| 📅 Année de référence population | **2020 (WorldPop)** |

---

<!-- 📸 IMAGE : Capture d'écran de la carte interactive avec les zones de risque visibles (rouge/orange/jaune) -->
<!-- Chemin suggéré : docs/screenshots/map_risk_zones.png -->

---

## 🗂️ Structure du Projet

```
flood-risk-abidjan/
│
├── data/
│   ├── raw/                        # Données brutes (jamais modifiées)
│   │   ├── dem/                    # DEM SRTM + produits hydrologiques
│   │   ├── population/             # WorldPop 2020
│   │   ├── admin/                  # Limites GADM
│   │   ├── osm/                    # Données OpenStreetMap
│   │   └── rainfall/               # Précipitations CHIRPS 2020
│   └── processed/                  # Données traitées
│       ├── dem_abidjan.tif
│       ├── population_abidjan.tif
│       ├── flood_zones/
│       ├── exposed_pop/
│       └── risk_index/
│
├── scripts/                        # Pipeline de traitement Python
│   ├── 01_extract_data.py
│   ├── 02_clip_to_abidjan.py
│   ├── 03_flood_zones.py
│   ├── 04_population_exposure.py
│   ├── 05_download_full_pois.py
│   ├── 06_infrastructure_risk.py
│   ├── 07_export_for_web.py
│   └── 09_simplify_geojson.py
│
├── maps/
│   └── static/                     # Cartes PNG exportées
│       ├── flood_risk_abidjan.png
│       ├── population_exposure.png
│       └── infrastructure_risk.png
│
├── web/                            # Dashboard interactif
│   ├── index.html                  # Application principale
│   └── assets/data/                # GeoJSON simplifiés
│
├── notebooks/                      # Analyses exploratoires
├── requirements.txt
└── README.md
```

---

## ⚙️ Méthodologie

### Étape 1 — Collecte des données multi-sources

Cinq sources de données complémentaires ont été acquises :

| Source | Donnée | Résolution |
|---|---|---|
| NASA / OpenTopography | DEM SRTM GL1 + hydrologie | 30m |
| WorldPop | Population résidentielle | 100m |
| GADM | Limites administratives niveau 3 | Vecteur |
| OpenStreetMap via OSMnx | Routes, bâtiments, POIs | Vecteur |
| CHIRPS v2.0 | Précipitations mensuelles 2020 | ~5km |

Le DEM a été téléchargé avec traitement hydrologique intégré : **DEM conditionné**, **accumulation de flux D8**, **Topographic Wetness Index** et **réseau de drainage vectorisé**.

### Étape 2 — Préparation et découpage spatial

Toutes les données raster ont été découpées sur l'emprise géographique d'Abidjan à l'aide des limites GADM comme masque de découpe (`rasterio.mask`). Le **DEM hydrologique conditionné** (`Hydro_Conditioned_DEM.tif`) a été utilisé plutôt que le DEM brut pour garantir la cohérence du réseau de drainage.

```python
# Exemple de découpage raster
with rasterio.open(dem_path) as src:
    out_image, out_transform = mask(src, abidjan_geometry, crop=True)
```

### Étape 3 — Modélisation des zones de risque

Classification du risque en trois niveaux basée sur l'altitude :

```
Haut risque   →  altitude < 10m   (zones basses, bords de lagune)
Risque modéré →  10m – 25m        (zones intermédiaires)
Faible risque →  25m – 50m        (zones relativement élevées)
```

> Validation : altitude min Abidjan = 2m (lagune), max = 146m, moyenne = 43m

<!-- 📸 IMAGE : Les deux cartes côte à côte (DEM relief + zones de risque) générées par matplotlib -->
<!-- Chemin suggéré : docs/screenshots/dem_vs_risk.png -->

### Étape 4 — Croisement avec les données sociales

- **Population exposée** : raster WorldPop rééchantillonné par interpolation bilinéaire, croisé pixel par pixel avec la carte de risque
- **Infrastructures critiques** : 3 688 POIs (hôpitaux, écoles, commissariats...) auxquels un niveau de risque est assigné par échantillonnage raster (`rasterio.sample`)
- **Bâtiments** : 392 618 bâtiments OSM classifiés selon le centroïde de leur géométrie

<!-- 📸 IMAGE : Graphique en barres (infrastructure_risk.png) montrant les 3 catégories par zone de risque -->
<!-- Chemin suggéré : docs/screenshots/infrastructure_risk.png -->

### Étape 5 — Dashboard interactif

Export des données en GeoJSON simplifié et développement d'un dashboard HTML/CSS/JS intégrant Leaflet.js et Chart.js.

---

## 🚀 Installation & Lancement

### Prérequis

- Python 3.10+
- pip

### Installation

```bash
# Cloner le dépôt
git clone https://github.com/votre-username/flood-risk-abidjan.git
cd flood-risk-abidjan

# Installer les dépendances
pip install -r requirements.txt
```

### Lancer la pipeline complète

```bash
# 1. Découper les données sur Abidjan
python scripts/02_clip_to_abidjan.py

# 2. Générer les zones de risque
python scripts/03_flood_zones.py

# 3. Calculer la population exposée
python scripts/04_population_exposure.py

# 4. Analyser les infrastructures
python scripts/06_infrastructure_risk.py

# 5. Exporter pour le web
python scripts/07_export_for_web.py
```

### Lancer le dashboard

```bash
cd web
python -m http.server 8000
# Ouvrir http://localhost:8000/index.html
```

### Dépendances Python

```
rasterio
geopandas
osmnx
numpy
matplotlib
shapely
```

---

## 🗺️ Dashboard Interactif

Le dashboard comprend 6 sections :

- **Accueil** — présentation du projet et chiffres clés
- **Problématique** — les 6 questions auxquelles le projet répond
- **Méthodologie** — pipeline complète étape par étape
- **Carte** — Leaflet.js interactif avec couches activables (zones de risque, infrastructures, équipements)
- **Statistiques** — graphiques Chart.js (population, infrastructures, bâtiments par zone)
- **Métadonnées** — sources complètes avec liens

<!-- 📸 IMAGE : Capture d'écran complète du dashboard avec la carte et les statistiques visibles -->
<!-- Chemin suggéré : docs/screenshots/full_dashboard.png -->

---

## 📦 Sources de Données

| Donnée | Organisation | Lien | Format | Année |
|---|---|---|---|---|
| DEM SRTM GL1 | NASA / USGS | [OpenTopography](https://portal.opentopography.org/raster?opentopoID=OTSRTM.082015.4326.1) | GeoTIFF | 2000 |
| Population | WorldPop — Univ. Southampton | [WorldPop Hub](https://hub.worldpop.org/geodata/listing?id=29) | GeoTIFF | 2020 |
| Limites admin. | GADM | [gadm.org](https://gadm.org/download_country.html) | GeoPackage | 2022 |
| Réseau OSM | OpenStreetMap | [openstreetmap.org](https://www.openstreetmap.org) | GeoJSON | 2024 |
| Précipitations | CHIRPS v2.0 — UCSB | [CHC UCSB](https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs/) | GeoTIFF | 2020 |

Toutes les données utilisées sont **librement accessibles** et **open source**.

---

## 🔭 Perspectives d'Amélioration

- [ ] Intégration de données historiques d'inondations (événements réels)
- [ ] Modélisation hydrodynamique (FIM — Flood Inundation Mapping)
- [ ] Analyse temporelle sur les précipitations CHIRPS 2010–2025
- [ ] Score de vulnérabilité composite (altitude + densité + infrastructure)
- [ ] Export de rapports PDF par commune
- [ ] Application mobile pour les équipes de terrain

---

## 👤 Auteur

**Valentin KODJO Kablan Martial**  
Licence Professionnelle — Géomatique & Stratégies Spatiales  
Université Félix Houphouët-Boigny (UFHB) · Cocody, Abidjan, Côte d'Ivoire

[![GitHub](https://img.shields.io/badge/GitHub-votre--username-black?style=flat-square&logo=github)](https://github.com/votre-username)
[![LinkedIn](https://img.shields.io/badge/LinkedIn-Valentin%20KODJO-blue?style=flat-square&logo=linkedin)](https://linkedin.com/in/votre-profil)

---

## 📄 Licence

Ce projet est sous licence MIT. Les données utilisées sont soumises aux licences de leurs sources respectives (NASA, WorldPop, OpenStreetMap ODbL, GADM, CHIRPS).

---

> *"Les inondations à Abidjan ne sont pas une fatalité — elles sont une équation géospatiale que la donnée peut résoudre."*
