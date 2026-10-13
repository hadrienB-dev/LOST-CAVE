
import json
from pathlib import Path

RACINE_PROJET = Path(__file__).resolve().parent.parent
FICHIER_CARTE = RACINE_PROJET / "assets" / "maps" / "level_1.json"

with FICHIER_CARTE.open("r", encoding="utf-8") as fichier:
    carte = json.load(fichier)

print("Dimensions :", carte["width"], "x", carte["height"])
print("Taille des cases :", carte["tilewidth"], "x", carte["tileheight"])

print("\n--- CALQUES ---")
for couche in carte["layers"]:
    print(
        "Nom :", couche["name"],
        "| Type :", couche["type"],
        "| Visible :", couche.get("visible", True)
    )
    
    if couche["type"] == "tilelayer":
        donnees = couche.get("data", [])
        cases_remplies = [gid for gid in donnees if (gid & 0x1FFFFFFF) != 0]

        print("  Nombre de cases :", len(donnees))
        print("  Cases remplies :", len(cases_remplies))
        print("  Identifiants utilisés :", sorted(set(
            gid & 0x1FFFFFFF for gid in cases_remplies
        )))

print("\n--- TILESETS ---")
for tileset in carte["tilesets"]:
    print("Nom :", tileset.get("name", "(nom externe)"))
    print("Premier identifiant :", tileset["firstgid"])
    print("Image :", tileset.get("image", tileset.get("source", "non indiquée")))
    print("Colonnes :", tileset.get("columns", "non indiquées"))
    print("Taille :", tileset.get("tilewidth"), "x", tileset.get("tileheight"))