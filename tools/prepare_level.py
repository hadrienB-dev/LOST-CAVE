
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

DOSSIER = Path(__file__).parent
CARTE_SOURCE = DOSSIER / "level_1.json"
CARTE_SORTIE = DOSSIER / "level_1_pyxel.json"
IMAGE_SORTIE = DOSSIER / "tileset_compact.png"
COULEUR_TRANSPARENCE = (212, 24, 108, 255)

with CARTE_SOURCE.open("r", encoding="utf-8") as f:
    carte = json.load(f)

# Lire le tileset externe référencé par Tiled.
ts = carte["tilesets"][0]
firstgid = ts["firstgid"]
fichier_tsx = (DOSSIER / ts["source"]).resolve()
racine = ET.parse(fichier_tsx).getroot()
dossier_tsx = fichier_tsx.parent

largeur = int(racine.get("tilewidth"))
hauteur = int(racine.get("tileheight"))
colonnes = int(racine.get("columns"))
marge = int(racine.get("margin", "0"))
espacement = int(racine.get("spacing", "0"))

element_image = racine.find("image")
image_source = (dossier_tsx / element_image.get("source")).resolve()

# Collecter les identifiants de tuiles utilisés.
gids_utilises = set()
animations = {}

for tuile in racine.findall("tile"):
    animation = tuile.find("animation")
    if animation is None:
        continue

    tile_id = int(tuile.get("id"))
    frames = [
        (int(frame.get("tileid")), int(frame.get("duration")))
        for frame in animation.findall("frame")
    ]
    animations[tile_id] = frames
    gids_utilises.add(tile_id)
    gids_utilises.update(frame_tile_id for frame_tile_id, _ in frames)

for couche in carte["layers"]:
    if couche["type"] != "tilelayer":
        continue

    for gid in couche.get("data", []):
        gid &= 0x1FFFFFFF  # Retirer les bits d'orientation Tiled.
        if gid:
            gids_utilises.add(gid - firstgid)

ids_tries = sorted(gids_utilises)
print("Tuiles utilisées :", len(ids_tries))

with Image.open(image_source) as image:
    image = image.convert("RGBA")

    # Une planche de 8 colonnes tient dans une banque 256 x 256.
    colonnes_compactes = 8
    lignes_compactes = (len(ids_tries) + 7) // 8

    if lignes_compactes > 8:
        raise ValueError(
            "Plus de 64 tuiles utilisées : il faudra répartir "
            "la planche sur plusieurs banques."
        )

    planche = Image.new(
        "RGBA",
        (colonnes_compactes * largeur, lignes_compactes * hauteur),
        COULEUR_TRANSPARENCE,
    )

    # Ancien GID -> nouvel indice compact.
    correspondance = {}

    for nouvel_indice, ancien_id in enumerate(ids_tries):
        sx = marge + (ancien_id % colonnes) * (largeur + espacement)
        sy = marge + (ancien_id // colonnes) * (hauteur + espacement)

        tuile = image.crop((sx, sy, sx + largeur, sy + hauteur))

        dx = (nouvel_indice % colonnes_compactes) * largeur
        dy = (nouvel_indice // colonnes_compactes) * hauteur
        planche.alpha_composite(tuile, (dx, dy))

        correspondance[ancien_id + firstgid] = nouvel_indice + 1

    planche.save(IMAGE_SORTIE)

# Réécrire les identifiants dans une copie de la carte.
for couche in carte["layers"]:
    if couche["type"] != "tilelayer":
        continue

    if "data" in couche:
        nouvelles_donnees = []

        for gid in couche["data"]:
            gid_original = gid
            flags = gid & 0xE0000000
            gid_simple = gid & 0x1FFFFFFF

            if gid_simple == 0:
                nouvelles_donnees.append(0)
            else:
                nouveau_gid = correspondance[gid_simple]
                nouvelles_donnees.append(nouveau_gid | flags)

        couche["data"] = nouvelles_donnees

# Remplacer la référence au tileset externe par un tileset intégré.
animations_compactes = [
    {
        "id": correspondance[tile_id + firstgid] - 1,
        "animation": [
            {
                "tileid": correspondance[frame_tile_id + firstgid] - 1,
                "duration": duration,
            }
            for frame_tile_id, duration in frames
        ],
    }
    for tile_id, frames in animations.items()
]

carte["tilesets"] = [{
    "firstgid": 1,
    "name": "tileset_compact",
    "tilewidth": largeur,
    "tileheight": hauteur,
    "tilecount": len(ids_tries),
    "columns": colonnes_compactes,
    "image": "tileset_compact.png",
    "imagewidth": colonnes_compactes * largeur,
    "imageheight": lignes_compactes * hauteur,
    "margin": 0,
    "spacing": 0,
    "tiles": animations_compactes,
}]

with CARTE_SORTIE.open("w", encoding="utf-8") as f:
    json.dump(carte, f)

print("Carte créée :", CARTE_SORTIE.name)
print("Tileset créé :", IMAGE_SORTIE.name)
print("Terminé.")