"""Chargement, mouvements et rendu des entites placees dans l'editeur."""

import json
import math
from pathlib import Path
import time

import pygame
import pyxel

from .config import (
    COULEUR_TRANSPARENCE,
    HAUTEUR_JOUEUR,
    LARGEUR_JOUEUR,
    TAILLE_TILE,
    VITESSE_SAUT,
)
from .tiled_map import FICHIER_CARTE


RACINE_PROJET = Path(__file__).resolve().parent.parent


class EntitesNiveau:
    def __init__(self, fichier_carte=FICHIER_CARTE):
        self.fichier_carte = Path(fichier_carte).resolve()
        self.fichier_entites = self.fichier_carte.with_name(
            f"{self.fichier_carte.stem}.entities.json"
        )
        self.entites = []
        self.images = {}
        self.directions = {}
        self.points_courants = {}
        self.origines = {}
        self.pas_courants = {}
        self.distance_restante = {}
        self.orientations = {}
        self.morts = {}
        self.dimensions_images = {}
        self.sons_effets = {}
        self.debut_animations = time.perf_counter()
        self.charger()

    def charger(self):
        if not self.fichier_entites.exists():
            self.entites = []
            return
        with self.fichier_entites.open("r", encoding="utf-8") as fichier:
            document = json.load(fichier)
        entites = document.get("entities")
        if not isinstance(entites, list):
            raise ValueError(
                f"La liste 'entities' est absente de {self.fichier_entites}."
            )
        for entite in entites:
            if not isinstance(entite, dict):
                raise ValueError("Chaque entite du niveau doit etre un objet JSON.")
            self._valider(entite)
            animation = entite.setdefault("animation", {})
            animation.setdefault("frame_width", TAILLE_TILE)
            animation.setdefault("frame_height", TAILLE_TILE)
            animation.setdefault("columns", 1)
            animation.setdefault("frame_count", 1)
            animation.setdefault("row", 0)
            animation.setdefault("fps", 8)
            animation.setdefault(
                "frame_delay_ms",
                1000 / max(0.1, float(animation.get("fps", 8))),
            )
            animation.setdefault("sequences", {})
            animation.setdefault("loop", True)
            animation.setdefault("offset_x", 0)
            animation.setdefault("offset_y", 0)
            animation.setdefault("flip_x", False)
            animation.setdefault("flip_y", False)
            entite.setdefault("movement", {})
            hitbox = entite.setdefault("hitbox", {})
            hitbox.setdefault("x", 4)
            hitbox.setdefault("y", 16)
            hitbox.setdefault("width", 24)
            hitbox.setdefault("height", 16)
            entite.setdefault("effects", {})
            entite.setdefault("visible", True)
            entite.setdefault("enabled", True)
            entite.setdefault("killable", False)
        self.entites = entites
        self.directions = {entite["id"]: 1 for entite in entites}
        self.points_courants = {entite["id"]: 0 for entite in entites}
        self.pas_courants = {entite["id"]: 0 for entite in entites}
        self.distance_restante = {
            entite["id"]: float(
                entite.get("movement", {}).get("steps", [{}])[0].get("steps", 0)
            )
            if entite.get("movement", {}).get("steps")
            else 0
            for entite in entites
        }
        self.orientations = {
            entite["id"]: (
                entite.get("movement", {}).get("facing")
                if entite.get("movement", {}).get("facing") in ("left", "right")
                else "right"
            )
            for entite in entites
        }
        self.morts = {}
        self.origines = {
            entite["id"]: (float(entite["x"]), float(entite["y"]))
            for entite in entites
        }
        self._charger_images()

    def _valider(self, entite):
        for cle in ("id", "x", "y", "width", "height"):
            if cle not in entite:
                raise ValueError(
                    f"La propriete '{cle}' est absente d'une entite dans "
                    f"{self.fichier_entites}."
                )
        for cle in ("x", "y", "width", "height"):
            valeur = entite[cle]
            if (
                isinstance(valeur, bool)
                or not isinstance(valeur, (int, float))
                or not math.isfinite(valeur)
            ):
                raise ValueError(f"La propriete '{cle}' d'une entite est invalide.")
        if entite["width"] <= 0 or entite["height"] <= 0:
            raise ValueError("La largeur et la hauteur d'une entite doivent etre positives.")

    def _charger_images(self):
        self.dimensions_images = {}
        for entite in self.entites:
            sprite = entite.get("sprite", "")
            if not sprite:
                continue
            chemin = Path(sprite)
            if not chemin.is_absolute():
                chemin = (RACINE_PROJET / chemin).resolve()
            if not chemin.is_file():
                raise FileNotFoundError(
                    f"Sprite introuvable pour l'entite '{entite['id']}' : {chemin}"
                )
            try:
                surface = pygame.image.load(str(chemin))
                largeur_image, hauteur_image = surface.get_size()
                if largeur_image > 256 or hauteur_image > 256:
                    raise ValueError("Pyxel limite les spritesheets a 256 x 256 pixels.")
                image = pyxel.Image(256, 256)
                image.load(0, 0, str(chemin))
                pixels = []
                for y in range(hauteur_image):
                    ligne = []
                    for x in range(largeur_image):
                        couleur = (
                            COULEUR_TRANSPARENCE
                            if surface.get_at((x, y)).a == 0
                            else image.pget(x, y)
                        )
                        ligne.append(format(couleur, "x"))
                    pixels.append("".join(ligne))
                image.set(0, 0, pixels)
            except (ValueError, RuntimeError) as erreur:
                raise ValueError(
                    f"Impossible de charger le sprite de l'entite "
                    f"'{entite['id']}' ({chemin}) : {erreur}"
                ) from erreur
            animation = entite["animation"]
            largeur = int(animation.get("frame_width", TAILLE_TILE))
            hauteur = int(animation.get("frame_height", TAILLE_TILE))
            colonnes = int(animation.get("columns", 1))
            lignes = math.ceil(int(animation.get("frame_count", 1)) / colonnes)
            if (
                largeur <= 0
                or hauteur <= 0
                or colonnes <= 0
                or largeur * colonnes > 256
                or hauteur * lignes > 256
            ):
                raise ValueError(
                    f"Les frames du sprite de l'entite '{entite['id']}' "
                    "depassent les dimensions prises en charge (256 x 256)."
                )
            sequences = animation.get("sequences", {})
            if not isinstance(sequences, dict):
                raise ValueError(
                    f"Les sequences d'animation de l'entite '{entite['id']}' "
                    "doivent etre un objet."
                )
            for nom in ("left", "right", "death"):
                frames = sequences.get(nom, [])
                if not isinstance(frames, list):
                    raise ValueError(
                        f"La sequence '{nom}' de l'entite '{entite['id']}' "
                        "doit etre une liste."
                    )
                for frame in frames:
                    if (
                        not isinstance(frame, dict)
                        or any(
                            isinstance(frame.get(cle), bool)
                            or not isinstance(frame.get(cle), int)
                            or frame[cle] < 0
                            for cle in ("column", "row")
                        )
                        or frame["column"] * largeur + largeur > largeur_image
                        or frame["row"] * hauteur + hauteur > hauteur_image
                    ):
                        raise ValueError(
                            f"Une frame de la sequence '{nom}' de l'entite "
                            f"'{entite['id']}' depasse le spritesheet."
                        )
            self.dimensions_images[entite["id"]] = (
                largeur_image,
                hauteur_image,
            )
            self.images[entite["id"]] = image

    def mettre_a_jour(self, joueur, ancienne_y=None, ancienne_vitesse_y=None):
        if ancienne_y is None:
            ancienne_y = joueur.y
        if ancienne_vitesse_y is None:
            ancienne_vitesse_y = joueur.velocity_y
        for entite in self.entites:
            if entite["id"] in self.morts:
                frames_mort = entite["animation"].get("sequences", {}).get(
                    "death", []
                )
                delai = self._delai_sequence(entite["animation"], "death")
                if (
                    not frames_mort
                    or (time.perf_counter() - self.morts[entite["id"]]) * 1000
                    >= len(frames_mort) * delai
                ):
                    del self.morts[entite["id"]]
                continue
            if not entite.get("enabled", True):
                continue
            self._mettre_a_jour_mouvement(entite, joueur)
            if not entite.get("collision", True):
                continue
            if entite.get("category") != "enemy":
                continue
            if not self._chevauche(entite, joueur):
                continue
            hitbox = self._hitbox(entite)
            hitbox_top = float(entite["y"]) + hitbox["y"]
            player_bottom_before = ancienne_y + HAUTEUR_JOUEUR
            player_bottom_after = joueur.y + HAUTEUR_JOUEUR
            landed_from_above = (
                ancienne_vitesse_y > 0
                and player_bottom_before <= hitbox_top + max(2, ancienne_vitesse_y)
                and player_bottom_after >= hitbox_top
            )
            if entite.get("killable", False) and landed_from_above:
                entite["enabled"] = False
                self._jouer_son_effet(entite)
                if entite["animation"].get("sequences", {}).get("death"):
                    self.morts[entite["id"]] = time.perf_counter()
                joueur.y = hitbox_top - HAUTEUR_JOUEUR
                joueur.velocity_y = VITESSE_SAUT * 0.55
                joueur.au_sol = False
                joueur.duree_saut = 0
                joueur.saut_en_attente = 0
                continue
            effet = entite.get("effects", {})
            if (
                effet.get("trigger", "contact") == "contact"
                and effet.get("action", "damage") == "damage"
                and effet.get("target", "player") in ("player", "all")
            ):
                self._jouer_son_effet(entite)
                joueur.reapparition_demandee = True

    def _mettre_a_jour_mouvement(self, entite, joueur):
        mouvement = entite["movement"]
        mode = mouvement.get("type", "stationary")
        if mode == "stationary":
            return
        vitesse = abs(float(mouvement.get("speed", 0)))
        if vitesse == 0:
            return
        if mode in ("horizontal", "vertical", "patrol"):
            axe = "y" if mode == "vertical" else mouvement.get("axis", "x")
            origine = self.origines[entite["id"]][0 if axe == "x" else 1]
            distance = max(0, float(mouvement.get("range", 0))) / 2
            minimum, maximum = origine - distance, origine + distance
            direction = self.directions.get(entite["id"], 1)
            ancienne_coordonnee = float(entite[axe])
            coordonnee = ancienne_coordonnee + vitesse * direction
            if coordonnee >= maximum:
                coordonnee = maximum
                direction = -1
            elif coordonnee <= minimum:
                coordonnee = minimum
                direction = 1
            entite[axe] = coordonnee
            self.directions[entite["id"]] = direction
            if axe == "x":
                self._orienter(entite, coordonnee - ancienne_coordonnee)
            return
        if mode == "loop":
            axe = mouvement.get("axis", "x")
            origine = self.origines[entite["id"]][0 if axe == "x" else 1]
            distance = max(0, float(mouvement.get("range", 0)))
            if distance:
                entite[axe] = origine + (float(entite[axe]) - origine + vitesse) % distance
                if axe == "x":
                    self._orienter(entite, 1)
            return
        if mode == "steps":
            steps = mouvement.get("steps", [])
            if not steps:
                return
            remaining_budget = vitesse
            while remaining_budget > 0:
                index = self.pas_courants[entite["id"]] % len(steps)
                self.pas_courants[entite["id"]] = index
                distance = min(
                    remaining_budget,
                    self.distance_restante[entite["id"]],
                )
                direction = steps[index]["direction"]
                axe, signe = {
                    "left": ("x", -1),
                    "right": ("x", 1),
                    "up": ("y", -1),
                    "down": ("y", 1),
                }[direction]
                entite[axe] += signe * distance
                if axe == "x":
                    self._orienter(entite, signe)
                remaining_budget -= distance
                self.distance_restante[entite["id"]] -= distance
                if self.distance_restante[entite["id"]] <= 0:
                    index = (index + 1) % len(steps)
                    self.pas_courants[entite["id"]] = index
                    self.distance_restante[entite["id"]] = float(
                        steps[index]["steps"]
                    )
            return
        if mode == "follow":
            dx = float(joueur.x) - float(entite["x"])
            dy = float(joueur.y) - float(entite["y"])
            longueur = math.hypot(dx, dy)
            if longueur:
                entite["x"] += dx / longueur * vitesse
                entite["y"] += dy / longueur * vitesse
                self._orienter(entite, dx)
            return
        if mode == "path":
            points = mouvement.get("waypoints", [])
            if not points:
                return
            index = self.points_courants.get(entite["id"], 0) % len(points)
            cible_x, cible_y = points[index]
            dx, dy = cible_x - entite["x"], cible_y - entite["y"]
            longueur = math.hypot(dx, dy)
            if longueur <= vitesse:
                entite["x"], entite["y"] = cible_x, cible_y
                self.points_courants[entite["id"]] = (index + 1) % len(points)
                self._orienter(entite, dx)
            elif longueur:
                entite["x"] += dx / longueur * vitesse
                entite["y"] += dy / longueur * vitesse
                self._orienter(entite, dx)
            return
        if mode == "projectile":
            axe = mouvement.get("axis", "x")
            direction = -1 if mouvement.get("facing") in ("left", "up") else 1
            entite[axe] += vitesse * direction
            if axe == "x":
                self._orienter(entite, direction)

    def _orienter(self, entite, direction):
        if direction:
            self.orientations[entite["id"]] = (
                "right" if direction > 0 else "left"
            )

    def _chevauche(self, entite, joueur):
        hitbox = self._hitbox(entite)
        gauche = float(entite["x"]) + hitbox["x"]
        haut = float(entite["y"]) + hitbox["y"]
        return (
            gauche < joueur.x + LARGEUR_JOUEUR
            and gauche + hitbox["width"] > joueur.x
            and haut < joueur.y + HAUTEUR_JOUEUR
            and haut + hitbox["height"] > joueur.y
        )

    @staticmethod
    def _hitbox(entite):
        hitbox = entite.get("hitbox", {})
        return {
            "x": float(hitbox.get("x", 0)),
            "y": float(hitbox.get("y", 0)),
            "width": float(hitbox.get("width", entite["width"])),
            "height": float(hitbox.get("height", entite["height"])),
        }

    def _jouer_son_effet(self, entite):
        chemin_son = entite.get("effects", {}).get("sound", "")
        if not chemin_son:
            return
        chemin = Path(chemin_son)
        if not chemin.is_absolute():
            chemin = (RACINE_PROJET / chemin).resolve()
        if not chemin.is_file():
            raise FileNotFoundError(
                f"Son introuvable pour l'entite '{entite['id']}' : {chemin}"
            )
        son = self.sons_effets.get(chemin)
        if son is None:
            son = pygame.mixer.Sound(str(chemin))
            self.sons_effets[chemin] = son
        son.play()

    @staticmethod
    def _delai_sequence(animation, nom_sequence):
        settings = animation.get("direction_settings", {}).get(nom_sequence, {})
        delai = settings.get("frame_delay_ms")
        if delai is None:
            delai = animation.get("frame_delay_ms", 125)
        return max(1, float(delai))

    def _retourner_sequence(self, animation, nom_sequence, orientation, axe):
        settings = animation.get("direction_settings", {}).get(nom_sequence, {})
        valeur = settings.get(f"flip_{axe}")
        if valeur is None:
            return animation.get(f"flip_{axe}", False)
        if isinstance(valeur, bool):
            return valeur
        if nom_sequence == "death" and valeur in (
            "direction_right", "direction_left"
        ):
            direction_cible = (
                "right" if valeur == "direction_right" else "left"
            )
            return orientation == direction_cible
        raise ValueError(
            f"Reglage flip_{axe} invalide pour la sequence '{nom_sequence}'."
        )

    def dessiner(self, camera_x=0, camera_y=0):
        maintenant = time.perf_counter()
        for entite in sorted(self.entites, key=lambda item: item.get("layer", 0)):
            est_mort = entite["id"] in self.morts
            if (
                not entite.get("visible", True)
                or (not entite.get("enabled", True) and not est_mort)
            ):
                continue
            image = self.images.get(entite["id"])
            if image is None:
                continue
            animation = entite["animation"]
            orientation = self.orientations.get(entite["id"], "right")
            nom_sequence = (
                "death" if est_mort else orientation
            )
            sequence = animation.get("sequences", {}).get(nom_sequence, [])
            if sequence:
                debut = (
                    self.morts[entite["id"]]
                    if est_mort
                    else self.debut_animations
                )
                delai = self._delai_sequence(animation, nom_sequence)
                frame = int((maintenant - debut) * 1000 / delai)
                if est_mort:
                    if frame >= len(sequence):
                        self.morts.pop(entite["id"], None)
                        continue
                    frame = min(frame, len(sequence) - 1)
                else:
                    frame %= len(sequence)
                source_x = sequence[frame]["column"] * int(animation["frame_width"])
                source_y = sequence[frame]["row"] * int(animation["frame_height"])
            else:
                if est_mort:
                    continue
                frame_count = max(1, int(animation.get("frame_count", 1)))
                fps = max(0.1, float(animation.get("fps", 8)))
                frame = int((maintenant - self.debut_animations) * fps)
                if animation.get("loop", True):
                    frame %= frame_count
                else:
                    frame = min(frame, frame_count - 1)
                columns = max(1, int(animation.get("columns", 1)))
                source_x = (frame % columns) * int(animation["frame_width"])
                source_y = (
                    int(animation.get("row", 0)) + frame // columns
                ) * int(animation["frame_height"])
            largeur = int(animation["frame_width"])
            hauteur = int(animation["frame_height"])
            flip_x = (
                self._retourner_sequence(animation, nom_sequence, orientation, "x")
                if sequence
                else animation.get("flip_x", False)
            )
            flip_y = (
                self._retourner_sequence(animation, nom_sequence, orientation, "y")
                if sequence
                else animation.get("flip_y", False)
            )
            if flip_x:
                largeur = -largeur
            if flip_y:
                hauteur = -hauteur
            pyxel.blt(
                int(entite["x"] - camera_x + animation.get("offset_x", 0)),
                int(entite["y"] - camera_y + animation.get("offset_y", 0)),
                image,
                source_x,
                source_y,
                largeur,
                hauteur,
                COULEUR_TRANSPARENCE,
            )
