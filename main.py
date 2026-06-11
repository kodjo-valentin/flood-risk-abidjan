from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os

# Initialisation de l'application FastAPI
app = FastAPI(
    title="Flood Risk Intelligence Abidjan",
    description="Serveur backend pour la cartographie des risques d'inondation"
)

# 1. On monte le dossier "web" pour que FastAPI serve automatiquement
# tous tes fichiers de données JS (flood_risk.js, critiques.js, etc.) et tes assets
if os.path.exists("web"):
    app.mount("/web", StaticFiles(directory="web"), name="web")

# 2. On sert ton fichier index.html qui est à la racine de ton projet


@app.get("/")
def distribuer_carte():
    return FileResponse("index.html")
