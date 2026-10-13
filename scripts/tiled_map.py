
import json
import time
from pathlib import Path
import pyxel


DOSSIER = Path(__file__).resolve().parent.parent / "assets" / "maps"
TAILLE_TILE = 32
COULEUR_TRANSPARENCE = 8
DUREE_ANIMATION_COLLECTE = 18
BANQUES_TILESET = (2, 1)
ORIGINES_Y_TILESET = (0, 160)
NOMS_CALQUES_COLLISION_COMPLETE = {
    "strict_collider",
}
NOMS_CALQUES_COLLISION = {
    "passages",
    *NOMS_CALQUES_COLLISION_COMPLETE,
}

FICHIER_CARTE = DOSSIER / "level_1_pyxel.json"
FICHIER_COLLISIONS = DOSSIER / "level_1.json"


class CarteTiled:
    def __init__(self):
        with FICHIER_CARTE.open("r", encoding="utf-8") as f:
            self.carte = json.load(f)

        with FICHIER_COLLISIONS.open("r", encoding="utf-8") as f:
            self.carte_originale = json.load(f)

        self.atlas = []
        self.animations = {}
        for atlas_index, tileset in enumerate(self.carte["tilesets"]):
            banque = BANQUES_TILESET[atlas_index]
            origine_y = ORIGINES_Y_TILESET[atlas_index]
            image = (FICHIER_CARTE.parent / tileset["image"]).resolve()
            pyxel.images[banque].load(0, origine_y, str(image))
            self.atlas.append({
                "firstgid": tileset["firstgid"],
                "tilecount": tileset["tilecount"],
                "columns": tileset["columns"],
                "bank": banque,
                "origin_y": origine_y,
            })
            for tuile in tileset.get("tiles", []):
                if not tuile.get("animation"):
                    continue
                self.animations[tileset["firstgid"] + tuile["id"]] = [
                    (
                        tileset["firstgid"] + frame["tileid"],
                        frame["duration"],
                    )
                    for frame in tuile["animation"]
                ]
        self.debut_animations = time.perf_counter()
        self.cranes_collectes = {}

        self.largeur = self.carte["width"] * TAILLE_TILE
        self.hauteur = self.carte["height"] * TAILLE_TILE

        # Conserver l'ordre Tiled, en séparant les calques dessinés devant le joueur.
        self.calques = [
            couche
            for couche in self.carte["layers"]
            if couche["type"] == "tilelayer"
            and couche.get("visible", True)
            and couche["name"].lower() not in NOMS_CALQUES_COLLISION
            and not couche["name"].endswith("_2")
        ]
        self.calques_devant = [
            couche
            for couche in self.carte["layers"]
            if couche["type"] == "tilelayer"
            and couche.get("visible", True)
            and couche["name"].lower() not in NOMS_CALQUES_COLLISION
            and couche["name"].endswith("_2")
        ]

        # Les positions de collision viennent du JSON original,
        # avant la conversion des identifiants.
        self.collisions = set()
        self.collisions_completes = set()
        self.acide = set()

        for couche in self.carte_originale["layers"]:
            if couche["type"] != "tilelayer":
                continue

            nom = couche["name"].lower()
            positions = (
                self.collisions
                if nom == "passages"
                else self.collisions_completes
                if nom in NOMS_CALQUES_COLLISION_COMPLETE
                else self.acide
                if nom.startswith("acide")
                else None
            )
            if positions is None:
                continue

            for index, gid in enumerate(couche.get("data", [])):
                gid &= 0x1FFFFFFF

                if gid != 0:
                    colonne = index % self.carte_originale["width"]
                    ligne = index // self.carte_originale["width"]
                    positions.add((colonne, ligne))

    def dessiner(self, camera_x=0, camera_y=0, devant=False):
        temps_animation_ms = int(
            (time.perf_counter() - self.debut_animations) * 1000
        )
        calques = self.calques_devant if devant else self.calques
        for couche in calques:
            donnees = couche.get("data", [])
            for index, gid_original in enumerate(donnees):
                gid = gid_original
                gid &= 0x1FFFFFFF

                if (
                    couche["name"] == "Gold_skulls_1"
                    and index in self.cranes_collectes
                ):
                    continue
                if gid == 0:
                    continue

                gid = self.gid_anime(gid, temps_animation_ms)

                # Les GID ont été compactés par prepare_level.py.
                banque, source_x, source_y = self.source_tuile(gid)

                colonne = index % self.carte["width"]
                ligne = index // self.carte["width"]

                x = colonne * TAILLE_TILE - camera_x
                y = ligne * TAILLE_TILE - camera_y

                # Ne dessiner que les tuiles visibles à l'écran.
                if (
                    x + TAILLE_TILE <= 0
                    or y + TAILLE_TILE <= 0
                    or x >= pyxel.width
                    or y >= pyxel.height
                ):
                    continue

                pyxel.blt(
                    x, y,
                    banque,
                    source_x, source_y,
                    TAILLE_TILE, TAILLE_TILE,
                    COULEUR_TRANSPARENCE,
                )

            if couche["name"] == "Gold_skulls_1":
                self.dessiner_cranes_collectes(
                    couche, camera_x, camera_y
                )

    def dessiner_cranes_collectes(self, couche, camera_x, camera_y):
        donnees = couche.get("data", [])
        for index, frame in self.cranes_collectes.items():
            gid = donnees[index] & 0x1FFFFFFF
            progress = frame / DUREE_ANIMATION_COLLECTE

            colonne = index % self.carte["width"]
            ligne = index // self.carte["width"]
            x = colonne * TAILLE_TILE - camera_x
            y = ligne * TAILLE_TILE - camera_y
            gid = self.gid_anime(
                gid,
                int((time.perf_counter() - self.debut_animations) * 1000),
            )
            banque, source_x, source_y = self.source_tuile(gid)
            pyxel.dither(1 - progress)
            pyxel.blt(
                int(x), int(y),
                banque,
                source_x,
                source_y,
                TAILLE_TILE, TAILLE_TILE,
                COULEUR_TRANSPARENCE,
            )
            pyxel.dither(1)

    def source_tuile(self, gid):
        for atlas in self.atlas:
            debut = atlas["firstgid"]
            if debut <= gid < debut + atlas["tilecount"]:
                indice = gid - debut
                return (
                    atlas["bank"],
                    (indice % atlas["columns"]) * TAILLE_TILE,
                    atlas["origin_y"]
                    + (indice // atlas["columns"]) * TAILLE_TILE,
                )
        raise ValueError(f"GID de tuile compact introuvable : {gid}")

    def mettre_a_jour_cranes_collectes(self):
        couche = next(
            (
                couche
                for couche in self.carte["layers"]
                if couche["type"] == "tilelayer"
                and couche["name"] == "Gold_skulls_1"
            ),
            None,
        )
        if couche is None:
            raise ValueError("Calque Gold_skulls_1 introuvable dans la carte")

        donnees = couche.get("data", [])
        for index, frame in tuple(self.cranes_collectes.items()):
            frame += 1
            if frame >= DUREE_ANIMATION_COLLECTE:
                donnees[index] = 0
                del self.cranes_collectes[index]
            else:
                self.cranes_collectes[index] = frame

    def gid_anime(self, gid, temps_ms):
        frames = self.animations.get(gid)
        if not frames:
            return gid

        duree_totale = sum(duree for _, duree in frames)
        if duree_totale <= 0:
            return gid

        temps_frame = temps_ms % duree_totale
        for gid_frame, duree in frames:
            if temps_frame < duree:
                return gid_frame
            temps_frame -= duree

        return gid

    def recolter_gold_skulls(self, x, y, largeur, hauteur):
        colonne_min = max(0, int(x // TAILLE_TILE))
        colonne_max = min(
            self.carte["width"] - 1,
            int((x + largeur - 1) // TAILLE_TILE),
        )
        ligne_min = max(0, int(y // TAILLE_TILE))
        ligne_max = min(
            self.carte["height"] - 1,
            int((y + hauteur - 1) // TAILLE_TILE),
        )
        recoltes = 0

        for couche in self.carte["layers"]:
            if (
                couche["type"] != "tilelayer"
                or couche["name"] != "Gold_skulls_1"
            ):
                continue

            donnees = couche.get("data", [])
            for ligne in range(ligne_min, ligne_max + 1):
                for colonne in range(colonne_min, colonne_max + 1):
                    index = ligne * self.carte["width"] + colonne
                    if (
                        donnees[index] & 0x1FFFFFFF
                        and index not in self.cranes_collectes
                    ):
                        self.cranes_collectes[index] = 0
                        recoltes += 1

        return recoltes

    def trouver_surface(self, colonne):
        if not 0 <= colonne < self.carte_originale["width"]:
            raise ValueError(f"Colonne de départ invalide : {colonne}")

        for ligne in range(self.carte_originale["height"]):
            if self.case_solide(colonne, ligne):
                return ligne * TAILLE_TILE

        raise ValueError(
            f"Aucune plateforme solide dans la colonne {colonne}"
        )

    def case_solide(self, colonne, ligne):
        return (
            0 <= colonne < self.carte_originale["width"]
            and 0 <= ligne < self.carte_originale["height"]
            and (
                (colonne, ligne) in self.collisions
                or (colonne, ligne) in self.collisions_completes
            )
        )

    def case_collision_complete(self, colonne, ligne):
        return (
            0 <= colonne < self.carte_originale["width"]
            and 0 <= ligne < self.carte_originale["height"]
            and (colonne, ligne) in self.collisions_completes
        )

    def chevauche_collision_complete(self, x, y, largeur, hauteur):
        colonne_min = max(0, int(x // TAILLE_TILE))
        colonne_max = min(
            self.carte_originale["width"] - 1,
            int((x + largeur - 1) // TAILLE_TILE),
        )
        ligne_min = max(0, int(y // TAILLE_TILE))
        ligne_max = min(
            self.carte_originale["height"] - 1,
            int((y + hauteur - 1) // TAILLE_TILE),
        )
        return any(
            self.case_collision_complete(colonne, ligne)
            for ligne in range(ligne_min, ligne_max + 1)
            for colonne in range(colonne_min, colonne_max + 1)
        )

    def case_acide(self, colonne, ligne):
        return (colonne, ligne) in self.acide