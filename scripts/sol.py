"""Gestion du sol décoratif."""

import pyxel
from .config import *

class Sol:
    def __init__(self):
        self.y = HAUTEUR_ECRAN - TAILLE_TILE

        # Arrondi supérieur pour couvrir toute la largeur
        self.nombre_tiles = (
            LARGEUR_ECRAN + TAILLE_TILE - 1
        ) // TAILLE_TILE

    def dessiner(self):
        for colonne in range(self.nombre_tiles):
            x = colonne * TAILLE_TILE

            pyxel.blt(
                x,
                self.y,
                BANQUE_SOL,
                0,
                ORIGINE_Y_SOL,
                TAILLE_TILE,
                TAILLE_TILE,
                COULEUR_TRANSPARENCE,
            )


# ============================================================
# JEU
# ============================================================

