
import json
import xml.etree.ElementTree as ET
from pathlib import Path

RACINE_PROJET = Path(__file__).resolve().parent.parent
DOSSIER_CARTES = RACINE_PROJET / "assets" / "maps"
FICHIER_CARTE = DOSSIER_CARTES / "level_1.json"

with FICHIER_CARTE.open("r", encoding="utf-8") as fichier:
    carte = json.load(fichier)

print("=== TILESET ===")

for ts in carte["tilesets"]:
    if "source" not in ts:
        print("Tileset intégré au JSON :", ts)
        continue

    fichier_tsx = (FICHIER_CARTE.parent / ts["source"]).resolve()
    print("Fichier TSX :", fichier_tsx)

    if not fichier_tsx.exists():
        print("ERREUR : fichier TSX introuvable.")
        continue

    racine = ET.parse(fichier_tsx).getroot()
    dossier_tsx = fichier_tsx.parent

    print("Taille des tuiles :", racine.get("tilewidth"), "x", racine.get("tileheight"))
    print("Nombre de tuiles :", racine.get("tilecount"))
    print("Colonnes :", racine.get("columns"))

    image = racine.find("image")
    if image is not None:
        chemin_image = (dossier_tsx / image.get("source", "")).resolve()
        print("Image :", chemin_image)
        print("Image présente :", chemin_image.exists())
        print("Dimensions déclarées :", image.get("width"), "x", image.get("height"))

print("\n=== IDENTIFIANTS UTILISÉS ===")

for couche in carte["layers"]:
    if couche["type"] != "tilelayer":
        continue

    donnees = couche.get("data", [])
    gids = sorted({
        valeur & 0x1FFFFFFF
        for valeur in donnees
        if valeur != 0
    })

    print(f"{couche['name']} : {len(gids)} identifiants différents")
    print("  Premiers identifiants :", gids[:20])