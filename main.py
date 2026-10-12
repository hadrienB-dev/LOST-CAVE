"""Point d’entrée de Lost Cave."""

import pyxel
from scripts.config import LARGEUR_ECRAN, HAUTEUR_ECRAN, TITRE
from scripts.jeu import Jeu


def main():
    pyxel.init(LARGEUR_ECRAN, HAUTEUR_ECRAN, title=TITRE, fps=60)
    pyxel.mouse(True)
    jeu = Jeu()
    pyxel.run(jeu.update, jeu.draw)


if __name__ == "__main__":
    main()