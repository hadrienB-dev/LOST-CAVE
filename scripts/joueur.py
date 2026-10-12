"""Logique et animation du personnage joueur."""

import pyxel
from math import sin, pi
from .config import *

class Joueur:
    def __init__(self, carte):
        self.x_depart = 2 * TAILLE_TILE
        self.y_depart = float(Y_DEPART)
        self.x = self.x_depart
        self.y = self.y_depart

        self.velocity_y = 0.0
        self.direction = 1
        self.moving = False
        self.au_sol = True
        self.saut_en_attente = 0
        self.duree_saut = 0
        self.impact_atterrissage = 0
        self.reapparition_demandee = False

    def update(self, carte, deplacement_force=None):
        self.impact_atterrissage = max(0, self.impact_atterrissage - 1)
        if deplacement_force is None:
            self.gerer_saut()
        self.deplacer_horizontalement(carte, deplacement_force)
        self.appliquer_gravite(carte)
        self.gerer_limites_carte(carte)
        if self.est_dans_acide(carte):
            self.reapparition_demandee = True

    def est_dans_acide(self, carte):
        colonne_min = int(self.x // TAILLE_TILE)
        colonne_max = int(
            (self.x + LARGEUR_JOUEUR - 1) // TAILLE_TILE
        )
        ligne_min = int(self.y // TAILLE_TILE)
        ligne_max = int(
            (self.y + HAUTEUR_JOUEUR - 1) // TAILLE_TILE
        )
        return any(
            carte.case_acide(colonne, ligne)
            for ligne in range(ligne_min, ligne_max + 1)
            for colonne in range(colonne_min, colonne_max + 1)
        )

    def reapparaitre(self):
        self.x = self.x_depart
        self.y = self.y_depart
        self.velocity_y = 0.0
        self.direction = 1
        self.moving = False
        self.au_sol = True
        self.saut_en_attente = 0
        self.duree_saut = 0
        self.impact_atterrissage = 0
        self.reapparition_demandee = False

    def deplacer_horizontalement(self, carte, deplacement_force=None):
        self.moving = False
        deplacement = 0

        if deplacement_force is not None:
            deplacement = deplacement_force
            self.direction = 1 if deplacement > 0 else -1
            self.moving = deplacement != 0
        elif pyxel.btn(pyxel.KEY_LEFT):
            deplacement = -VITESSE_DEPLACEMENT
            self.direction = -1
            self.moving = True

        elif pyxel.btn(pyxel.KEY_RIGHT):
            deplacement = VITESSE_DEPLACEMENT
            self.direction = 1
            self.moving = True

        x_candidat = self.x + deplacement
        if not carte.chevauche_collision_complete(
            x_candidat, self.y, LARGEUR_JOUEUR, HAUTEUR_JOUEUR
        ):
            self.x = x_candidat

    def gerer_saut(self):
        if pyxel.btnp(pyxel.KEY_SPACE):
            self.saut_en_attente = TOLERANCE_SAUT_FRAMES

        if self.saut_en_attente > 0 and self.au_sol:
            self.velocity_y = VITESSE_SAUT
            self.au_sol = False
            self.saut_en_attente = 0
            self.duree_saut = 0
            pyxel.play(1, 1)
        elif self.saut_en_attente > 0:
            self.saut_en_attente -= 1

    def appliquer_gravite(self, carte):
        ancienne_y = self.y
        etait_au_sol = self.au_sol
        self.velocity_y += GRAVITE
        if (
            self.velocity_y < 0
            and self.duree_saut < DUREE_SAUT_MAX_FRAMES
            and pyxel.btn(pyxel.KEY_SPACE)
        ):
            self.velocity_y -= FORCE_SAUT_MAINTENU
            self.duree_saut += 1

        self.y += self.velocity_y

        if self.y < 0:
            self.y = 0
            self.velocity_y = 0
            self.au_sol = False
            return

        colonne_min = int(self.x // TAILLE_TILE)
        colonne_max = int(
            (self.x + LARGEUR_JOUEUR - 1) // TAILLE_TILE
        )

        if self.velocity_y < 0:
            ancienne_haut = ancienne_y
            nouvelle_haut = self.y
            premiere_ligne = max(
                0, int((nouvelle_haut - 1) // TAILLE_TILE)
            )
            derniere_ligne = min(
                carte.carte_originale["height"] - 1,
                int((ancienne_haut - 1) // TAILLE_TILE),
            )
            for ligne in range(premiere_ligne, derniere_ligne + 1):
                bas_tuile = (ligne + 1) * TAILLE_TILE
                if not nouvelle_haut <= bas_tuile <= ancienne_haut:
                    continue
                for colonne in range(colonne_min, colonne_max + 1):
                    if carte.case_collision_complete(colonne, ligne):
                        self.y = bas_tuile
                        self.velocity_y = 0
                        self.au_sol = False
                        return

        self.au_sol = False
        if self.velocity_y > 0:
            ancienne_bas = ancienne_y + HAUTEUR_JOUEUR
            nouvelle_bas = self.y + HAUTEUR_JOUEUR
            premiere_ligne = max(
                0, int(ancienne_bas // TAILLE_TILE)
            )
            derniere_ligne = min(
                carte.carte_originale["height"] - 1,
                int(nouvelle_bas // TAILLE_TILE),
            )

            for ligne in range(premiere_ligne, derniere_ligne + 1):
                haut_tuile = ligne * TAILLE_TILE
                if not ancienne_bas <= haut_tuile <= nouvelle_bas:
                    continue
                for colonne in range(colonne_min, colonne_max + 1):
                    if carte.case_solide(colonne, ligne):
                        self.y = haut_tuile - HAUTEUR_JOUEUR
                        self.velocity_y = 0
                        self.au_sol = True
                        if not etait_au_sol:
                            self.impact_atterrissage = 6
                            pyxel.play(1, 3)
                        return

    def gerer_limites_carte(self, carte):
        self.x = max(
            0,
            min(self.x, carte.largeur - LARGEUR_JOUEUR)
        )

    def dessiner(self, camera_x=0, camera_y=0):
        if not self.au_sol:
            source_x = DEBUT_SPRITESHEET_SAUT
            source_y = 0 if self.direction == 1 else HAUTEUR_JOUEUR
        elif self.moving:
            frame = (
                pyxel.frame_count // VITESSE_ANIMATION
            ) % 4
            source_x = frame * LARGEUR_JOUEUR
            source_y = 0 if self.direction == 1 else HAUTEUR_JOUEUR
        else:
            source_x = 0
            source_y = 0 if self.direction == 1 else HAUTEUR_JOUEUR

        echelle = 1.0
        if self.impact_atterrissage > 0:
            phase = self.impact_atterrissage / 6
            echelle -= 0.15 * sin(pi * phase)

        largeur = round(LARGEUR_JOUEUR * echelle)
        hauteur = round(HAUTEUR_JOUEUR * echelle)
        pyxel.blt(
            int(self.x + (LARGEUR_JOUEUR - largeur) / 2 - camera_x),
            int(self.y + HAUTEUR_JOUEUR - hauteur - camera_y),
            BANQUE_JOUEUR,
            source_x,
            source_y,
            LARGEUR_JOUEUR,
            HAUTEUR_JOUEUR,
            COULEUR_TRANSPARENCE,
            0,
            echelle,
        )


# ============================================================
# SOL
# ============================================================

