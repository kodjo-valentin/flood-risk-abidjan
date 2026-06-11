from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = Path(__file__).resolve().parent

# Initialisation de l'application FastAPI
app = FastAPI(
    title="Flood Risk Intelligence Abidjan",
    description="Serveur backend pour la cartographie des risques d'inondation"
)

# 1. On monte le dossier "web" avec un chemin absolu pour éviter les erreurs
# si Uvicorn est lancé depuis un autre répertoire (cas classique sur Render).
web_dir = BASE_DIR / "web"
if web_dir.exists():
    app.mount("/web", StaticFiles(directory=str(web_dir)), name="web")

# 2. On sert ton fichier index.html qui est à la racine de ton projet


@app.get("/")
def distribuer_carte():
    return FileResponse(BASE_DIR / "index.html")
