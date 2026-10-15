"""Point d’entrée de Lost Cave."""

import argparse


def main(argv=None):
    parser = argparse.ArgumentParser(description="Lost Cave")
    parser.add_argument(
        "--editor",
        action="store_true",
        help="ouvrir l'editeur de placements et de comportements",
    )
    parser.add_argument(
        "--map",
        help="carte Tiled JSON a ouvrir dans l'editeur",
    )
    arguments = parser.parse_args(argv)

    if arguments.editor:
        from tools.level_entity_editor import launch

        launch(arguments.map)
        return

    if arguments.map:
        parser.error("--map ne peut etre utilise qu'avec --editor")

    import pyxel
    from scripts.config import LARGEUR_ECRAN, HAUTEUR_ECRAN, TITRE
    from scripts.jeu import Jeu

    pyxel.init(LARGEUR_ECRAN, HAUTEUR_ECRAN, title=TITRE, fps=60)
    pyxel.mouse(True)
    jeu = Jeu()
    pyxel.run(jeu.update, jeu.draw)


if __name__ == "__main__":
    main()