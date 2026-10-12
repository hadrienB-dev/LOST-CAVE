<<<<<<< HEAD
# Lost Cave — architecture refactorisée

## Lancer le jeu

Depuis le dossier du projet :

```bash
pip install -r requirements.txt
python main.py
```

Lancement depuis la racine du projet requis pour que les chemins des ressources `assets/...` soient résolus de manière identique.

## Organisation

- `main.py` : point d’entrée Pyxel uniquement.
- `scripts/config.py` : constantes de configuration et chemins des ressources.
- `scripts/joueur.py` : physique, déplacements, sauts et rendu du joueur.
- `scripts/sol.py` : rendu du sol.
- `scripts/jeu.py` : état du jeu, menu, intro, transitions, HUD et boucle de jeu.
- `scripts/tiled_map.py` : chargement, collisions et rendu de la carte Tiled.
- `assets/sprites/` : images et spritesheets.
- `assets/audio/` : musique et effets sonores.
- `assets/pyxel/` : fichiers de ressources Pyxel.
- `assets/maps/` : cartes et fichiers Tiled.
- `assets/source/` : fichiers source graphiques annexes.
- `tools/` : scripts utilitaires d’inspection et de préparation.

La séparation est structurelle : les classes et leur logique ont été déplacées sans réécrire leurs algorithmes. Les chemins des ressources ont été adaptés à leur nouvel emplacement.
=======
# LOST-CAVE-project
Repo github du platformer 2D d'horreur "LOST CAVE", codé dans le cadre d'un projet en NSI, en python avec l'engine "pyxel"
>>>>>>> 7eeae68 (Initial commit)
