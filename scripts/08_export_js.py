import json
from pathlib import Path

web_dir = Path('web/assets/data')

for fname in ['flood_risk.geojson', 'critiques.geojson', 'equipements.geojson']:
    with open(web_dir / fname) as f:
        data = json.load(f)
    varname = fname.replace('.geojson', '').replace('-', '_').replace(' ', '_')
    js = 'const DATA_' + varname.upper() + ' = ' + json.dumps(data) + ';'
    with open(web_dir / (varname + '.js'), 'w') as f:
        f.write(js)
    print('OK ' + varname + '.js - ' + str(len(data['features'])) + ' features')