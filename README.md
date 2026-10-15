# Lost Cave

Jeu de plateforme 2D d'horreur realise en Python avec Pyxel.

## Lancer le jeu

Depuis la racine du projet :

```bash
pip install -r requirements.txt
python main.py
```

## Editeur de niveau

L'editeur permet de previsualiser une carte Tiled, d'y placer et de deplacer
des ennemis, des objets et des elements speciaux, puis de configurer leurs
spritesheets, animations, mouvements, collisions, effets et donnees JSON
personnalisees.

```bash
python main.py --editor
```

Une autre carte Tiled JSON peut etre ouverte directement :

```bash
python main.py --editor --map assets/maps/level_1_pyxel.json
```

L'editeur enregistre ses donnees dans un fichier annexe, par exemple
`assets/maps/level_1_pyxel.entities.json`. Les cartes et tilesets existants ne
sont pas modifies. Le jeu charge ce fichier au demarrage et dessine les sprites
et leurs animations a la position enregistree. Les modes de mouvement
stationnaire, horizontal, vertical, patrouille, poursuite, chemin et projectile
sont pris en charge; le mode loop revient au point de depart apres la distance
definie. Le mode « steps » permet de creer une suite ordonnee de deplacements
gauche, droite, haut et bas, chacun avec une distance en pixels; la sequence se
repete en boucle. La vitesse determine la distance parcourue par frame. Chaque
entite peut avoir une hitbox personnalisee, visible en cyan dans l'editeur.
Les ennemis peuvent etre rendus tuables : un saut par-dessus les
elimine et fait rebondir le joueur. Un ennemi non tuable configure pour infliger
des degats declenche la reapparition du joueur au contact. Les autres effets et
interactions d'objets restent configurables, mais ne sont pas encore appliques
par la logique du jeu.

Dans l'onglet **Sprite**, choisissez un delai entre les frames en millisecondes
et creez visuellement des sequences gauche, droite et mort. **Parcourir le
spritesheet...** ouvre une grille cliquable : selectionnez une case, puis
ajoutez-la a la sequence courante; les boutons permettent ensuite de supprimer
ou de reordonner les frames. Les animations gauche/droite suivent le sens du
mouvement. Une animation de mort est jouee apres avoir ecrase un ennemi tuable,
puis celui-ci disparait. Les anciens spritesheets sans sequence configuree
continuent d'utiliser les reglages d'animation generiques. Chaque sequence peut
definir son propre delai et ses retournements X/Y; pour « death », un retournement
peut aussi dependre de l'orientation de l'ennemi au moment de sa mort.

Dans l'editeur, cliquer sur **Ennemi**, **Objet** ou **Special**, puis sur la
carte pour placer une entite. Cliquer-glisser une entite la deplace. Les
positions sont exprimees en pixels; la grille permet de les aligner sur les
cases de 32 pixels. `Ctrl+S` enregistre et `Echap` annule le mode de placement.
Dans la liste des entites, le menu contextuel permet de copier, coller ou
dupliquer une entite avec tous ses parametres; `Ctrl+C` et `Ctrl+V` copient et
collent egalement l'entite selectionnee.

## Organisation

- `main.py` : lancement du jeu ou de l'editeur.
- `scripts/` : boucle de jeu, personnage, configuration et carte Tiled.
- `tools/level_entity_editor.py` : editeur graphique des entites de niveau.
- `assets/sprites/` et `assets/audio/` : ressources du jeu.
- `assets/maps/` : cartes Tiled et donnees annexes.
