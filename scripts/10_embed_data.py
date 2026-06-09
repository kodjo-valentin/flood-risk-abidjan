import json
from pathlib import Path

web_dir = Path('web/assets/data')
html_path = Path('web/index.html')

# Lire les données
print("Lecture des données...")
with open(web_dir / 'flood_risk_simplified.geojson') as f:
    flood = json.load(f)
with open(web_dir / 'critiques.geojson') as f:
    critiques = json.load(f)
with open(web_dir / 'equipements.geojson') as f:
    equipements = json.load(f)

# Créer le bloc de données
data_block = f"""<!-- DATA EMBEDDED -->
<script>
const DATA_FLOOD_RISK = {json.dumps(flood)};
const DATA_CRITIQUES = {json.dumps(critiques)};
const DATA_EQUIPEMENTS = {json.dumps(equipements)};
</script>"""

# Lire le HTML
with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Remplacer les balises script src
old = '<script src="assets/data/flood_risk.js"></script>\n<script src="assets/data/critiques.js"></script>\n<script src="assets/data/equipements.js"></script>'
new_html = html.replace(old, data_block)

# Sauvegarder
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Données intégrées directement dans index.html")