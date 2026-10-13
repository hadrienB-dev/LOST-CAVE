
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image

RACINE_PROJET = Path(__file__).resolve().parent.parent
DOSSIER_CARTES = RACINE_PROJET / "assets" / "maps"
DOSSIER_SPRITES = RACINE_PROJET / "assets" / "sprites"
CARTE_SOURCE = DOSSIER_CARTES / "level_1.json"
CARTE_SORTIE = DOSSIER_CARTES / "level_1_pyxel.json"
IMAGE_SORTIE = DOSSIER_SPRITES / "tileset_compact.png"
IMAGE_SORTIE_SUPPLEMENTAIRE = DOSSIER_SPRITES / "tileset_compact_2.png"
COULEUR_TRANSPARENCE = (212, 24, 108, 255)
CAPACITE_ATLAS = 64
CAPACITE_ATLAS_SUPPLEMENTAIRE = 24

with CARTE_SOURCE.open("r", encoding="utf-8") as f:
    carte = json.load(f)

# Lire le tileset externe référencé par Tiled.
ts = carte["tilesets"][0]
firstgid = ts["firstgid"]
fichier_tsx = (CARTE_SOURCE.parent / ts["source"]).resolve()
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

    colonnes_compactes = 8
    if len(ids_tries) > CAPACITE_ATLAS + CAPACITE_ATLAS_SUPPLEMENTAIRE:
        raise ValueError(
            "Le niveau dépasse la capacité de 88 tuiles des deux atlas Pyxel."
        )

    nombres_par_atlas = [min(len(ids_tries), CAPACITE_ATLAS)]
    if len(ids_tries) > CAPACITE_ATLAS:
        nombres_par_atlas.append(len(ids_tries) - CAPACITE_ATLAS)
    planches = [
        Image.new(
            "RGBA",
            (
                colonnes_compactes * largeur,
                ((nombre + colonnes_compactes - 1) // colonnes_compactes)
                * hauteur,
            ),
            COULEUR_TRANSPARENCE,
        )
        for nombre in nombres_par_atlas
    ]

    # Ancien GID -> nouvel indice compact.
    correspondance = {}

    for nouvel_indice, ancien_id in enumerate(ids_tries):
        sx = marge + (ancien_id % colonnes) * (largeur + espacement)
        sy = marge + (ancien_id // colonnes) * (hauteur + espacement)

        tuile = image.crop((sx, sy, sx + largeur, sy + hauteur))

        atlas_indice = nouvel_indice // CAPACITE_ATLAS
        indice_local = nouvel_indice % CAPACITE_ATLAS
        dx = (indice_local % colonnes_compactes) * largeur
        dy = (indice_local // colonnes_compactes) * hauteur
        planches[atlas_indice].alpha_composite(tuile, (dx, dy))

        correspondance[ancien_id + firstgid] = nouvel_indice + 1

    planches[0].save(IMAGE_SORTIE)
    if len(planches) > 1:
        planches[1].save(IMAGE_SORTIE_SUPPLEMENTAIRE)
    else:
        IMAGE_SORTIE_SUPPLEMENTAIRE.unlink(missing_ok=True)

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
tilesets_compacts = []
for atlas_indice, nombre in enumerate(nombres_par_atlas):
    debut = atlas_indice * CAPACITE_ATLAS
    animations_compactes = []

    for tile_id, frames in animations.items():
        nouvel_id = correspondance[tile_id + firstgid] - 1
        if nouvel_id // CAPACITE_ATLAS != atlas_indice:
            continue

        animations_compactes.append({
            "id": nouvel_id - debut,
            "animation": [
                {
                    "tileid": correspondance[frame_tile_id + firstgid]
                    - debut - 1,
                    "duration": duration,
                }
                for frame_tile_id, duration in frames
            ],
        })

    lignes = (nombre + colonnes_compactes - 1) // colonnes_compactes
    nom_image = (
        "../sprites/tileset_compact.png"
        if atlas_indice == 0
        else "../sprites/tileset_compact_2.png"
    )
    tilesets_compacts.append({
        "firstgid": debut + 1,
        "name": f"tileset_compact_{atlas_indice + 1}",
        "tilewidth": largeur,
        "tileheight": hauteur,
        "tilecount": nombre,
        "columns": colonnes_compactes,
        "image": nom_image,
        "imagewidth": colonnes_compactes * largeur,
        "imageheight": lignes * hauteur,
        "margin": 0,
        "spacing": 0,
        "tiles": animations_compactes,
    })

carte["tilesets"] = tilesets_compacts

with CARTE_SORTIE.open("w", encoding="utf-8") as f:
    json.dump(carte, f)

print("Carte créée :", CARTE_SORTIE.name)
print("Tileset créé :", IMAGE_SORTIE.name)
print("Terminé.")