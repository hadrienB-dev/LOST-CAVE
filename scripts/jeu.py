"""Boucle de jeu, états, interface et rendu."""

import time
import pyxel
from .config import *
from .joueur import Joueur
from .sol import Sol
from .tiled_map import CarteTiled

class Jeu:
    def __init__(self):
        self.charger_ressources()
        self.carte = CarteTiled()

        self.etat = "menu"
        self.joueur = Joueur(self.carte)
        self.sol = Sol()
        self.gold_skulls = 0
        self.transition_fondu = None
        self.frame_fondu = 0
        self.phase_intro = None
        self.frames_marche_intro = 0
        self.dialogue_intro = 0
        self.caracteres_dialogue = 0
        self.frames_caractere_dialogue = 0
        self.fps = 0
        self.frames_ecoulees = 0
        self.temps_mesure_fps = time.perf_counter()
        pyxel.sounds[0].pcm(FICHIER_MUSIQUE)
        pyxel.channels[1].gain = VOLUME_SAUT
        pyxel.sounds[1].pcm(FICHIER_SAUT)
        pyxel.sounds[3].pcm(FICHIER_FIN_SAUT)
        pyxel.sounds[2].pcm(FICHIER_MUSIQUE_TITRE)
        pyxel.sounds[4].pcm(FICHIER_COLLECTE_CRANE)
        pyxel.play(0, 2, loop=True)

    def charger_ressources(self):
        # Charge les ressources du fichier .pyxres
        pyxel.load(FICHIER_RESSOURCES)

        # Charge les images PNG dans des banques distinctes
        pyxel.images[BANQUE_JOUEUR].load(
            0, 0, FICHIER_SPRITESHEET
        )
        pyxel.images[BANQUE_JOUEUR].load(
            DEBUT_SPRITESHEET_SAUT, 0, FICHIER_SPRITESHEET_SAUT
        )

        pyxel.images[BANQUE_FOND].load(
            0, 0, FICHIER_FOND
        )

        pyxel.images[BANQUE_TITRE].load(
            0, ORIGINE_Y_FOND_TITRE, FICHIER_FOND_TITRE
        )
        pyxel.images[BANQUE_SOL].load(
            0, 136, FICHIER_SOL
        )

    def update(self):
        if self.etat == "menu":
            self.update_menu()
            return
        if self.etat == "credits":
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                if self.bouton_survole(74, 105, 92, 18):
                    self.etat = "menu"
            if pyxel.btnp(pyxel.KEY_ESCAPE):
                self.etat = "menu"
            return
        if self.etat == "touches":
            if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
                if self.bouton_survole(74, 105, 92, 18):
                    self.etat = "menu"
            if pyxel.btnp(pyxel.KEY_ESCAPE):
                self.etat = "menu"
            return

        if self.transition_fondu is not None:
            self.update_fondu()
            return

        self.carte.mettre_a_jour_cranes_collectes()

        if self.phase_intro == "marche":
            self.joueur.update(self.carte, VITESSE_DEPLACEMENT)
            self.frames_marche_intro += 1
            if self.joueur.reapparition_demandee:
                self.phase_intro = None
                self.transition_fondu = "sortie"
                self.frame_fondu = 0
                return
            if self.frames_marche_intro >= (
                NOMBRE_PAS_INTRO * VITESSE_ANIMATION
            ):
                self.joueur.moving = False
                self.phase_intro = "dialogue"
                self.caracteres_dialogue = 0
                self.frames_caractere_dialogue = 0
            return

        if self.phase_intro == "dialogue":
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                nombre_caracteres = sum(
                    len(ligne)
                    for ligne in LIGNES_DIALOGUE_INTRO[self.dialogue_intro]
                )
                if self.caracteres_dialogue < nombre_caracteres:
                    self.caracteres_dialogue = nombre_caracteres
                else:
                    self.dialogue_intro += 1
                    if self.dialogue_intro >= len(LIGNES_DIALOGUE_INTRO):
                        self.phase_intro = None
                    else:
                        self.caracteres_dialogue = 0
                        self.frames_caractere_dialogue = 0
                return

            nombre_caracteres = sum(
                len(ligne)
                for ligne in LIGNES_DIALOGUE_INTRO[self.dialogue_intro]
            )
            if self.caracteres_dialogue < nombre_caracteres:
                self.frames_caractere_dialogue += 1
                if (
                    self.frames_caractere_dialogue
                    >= FRAMES_PAR_CARACTERE_DIALOGUE
                ):
                    self.caracteres_dialogue += 1
                    self.frames_caractere_dialogue = 0
            return

        self.joueur.update(self.carte)
        if self.joueur.reapparition_demandee:
            self.transition_fondu = "sortie"
            self.frame_fondu = 0
            return

        cranes_recoltes = self.carte.recolter_gold_skulls(
            self.joueur.x,
            self.joueur.y,
            LARGEUR_JOUEUR,
            HAUTEUR_JOUEUR,
        )
        self.gold_skulls += cranes_recoltes
        if cranes_recoltes:
            pyxel.play(2, 4)
        self.frames_ecoulees += 1
        temps_actuel = time.perf_counter()
        duree_mesure = temps_actuel - self.temps_mesure_fps

        if duree_mesure >= 1:
            self.fps = round(self.frames_ecoulees / duree_mesure)
            self.frames_ecoulees = 0
            self.temps_mesure_fps = temps_actuel

    def bouton_survole(self, x, y, largeur, hauteur):
        return (
            x <= pyxel.mouse_x < x + largeur
            and y <= pyxel.mouse_y < y + hauteur
        )

    def update_menu(self):
        if pyxel.btnp(pyxel.MOUSE_BUTTON_LEFT):
            if self.bouton_survole(132, 43, 94, 18):
                self.demarrer_jeu()
            elif self.bouton_survole(132, 67, 94, 18):
                self.etat = "credits"
            elif self.bouton_survole(132, 91, 94, 18):
                pyxel.quit()

        if pyxel.btnp(pyxel.KEY_RETURN):
            self.demarrer_jeu()
        elif pyxel.btnp(pyxel.KEY_C):
            self.etat = "credits"
        elif pyxel.btnp(pyxel.KEY_K):
            self.etat = "touches"

    def demarrer_jeu(self):
        self.etat = "jeu"
        self.transition_fondu = "entree"
        self.frame_fondu = 0
        self.phase_intro = "marche"
        self.frames_marche_intro = 0
        self.dialogue_intro = 0
        self.caracteres_dialogue = 0
        self.frames_caractere_dialogue = 0
        pyxel.play(0, 0, loop=True)

    def update_fondu(self):
        self.frame_fondu += 1
        if self.frame_fondu < DUREE_FONDU_FRAMES:
            return

        if self.transition_fondu == "sortie":
            self.joueur.reapparaitre()
            self.transition_fondu = "entree"
            self.frame_fondu = 0
        else:
            self.transition_fondu = None
            self.frame_fondu = 0

    def dessiner_fondu(self):
        if self.transition_fondu == "sortie":
            opacite = self.frame_fondu / DUREE_FONDU_FRAMES
        elif self.transition_fondu == "entree":
            opacite = 1 - self.frame_fondu / DUREE_FONDU_FRAMES
        else:
            return

        pyxel.dither(max(0, min(1, opacite)))
        pyxel.rect(0, 0, pyxel.width, pyxel.height, 0)
        pyxel.dither(1)

    def dessiner_bouton(self, texte, x, y, largeur, hauteur):
        survole = self.bouton_survole(x, y, largeur, hauteur)
        couleur_fond = 9 if survole else 1
        couleur_bord = 10 if survole else 7
        pyxel.rect(x, y, largeur, hauteur, couleur_fond)
        pyxel.rectb(x, y, largeur, hauteur, couleur_bord)
        pyxel.text(
            x + (largeur - len(texte) * 4) // 2,
            y + (hauteur - 5) // 2,
            texte,
            couleur_bord,
        )

    def dessiner_menu(self):
        pyxel.blt(
            0, 0, BANQUE_TITRE,
            0, ORIGINE_Y_FOND_TITRE,
            LARGEUR_ECRAN, HAUTEUR_ECRAN,
        )
        self.dessiner_bouton("JOUER", 132, 43, 94, 18)
        self.dessiner_bouton("CREDITS", 132, 67, 94, 18)
        self.dessiner_bouton("QUITTER", 132, 91, 94, 18)
        pyxel.text(8, 120, "K : TOUCHES", 7)

    def dessiner_credits(self):
        pyxel.blt(
            0, 0, BANQUE_TITRE,
            0, ORIGINE_Y_FOND_TITRE,
            LARGEUR_ECRAN, HAUTEUR_ECRAN,
        )
        pyxel.rect(108, 20, 122, 94, 1)
        pyxel.rectb(108, 20, 122, 94, 7)
        pyxel.text(148, 30, "CREDITS", 10)
        pyxel.text(121, 49, "Par Orb Studio :", 7)
        pyxel.text(121, 61, "- Hadrien BOISSY\n- Louka ROBIN\n- Raphael GADENNE\n\nREALISE EN PYTHON", 7)
        self.dessiner_bouton("RETOUR", 74, 105, 92, 18)

    def dessiner_touches(self):
        pyxel.blt(
            0, 0, BANQUE_TITRE,
            0, ORIGINE_Y_FOND_TITRE,
            LARGEUR_ECRAN, HAUTEUR_ECRAN,
        )
        pyxel.rect(24, 25, 192, 72, 1)
        pyxel.rectb(24, 25, 192, 72, 7)
        pyxel.text(96, 36, "TOUCHES", 10)
        pyxel.text(45, 54, "GAUCHE / DROITE : SE DEPLACER", 7)
        pyxel.text(45, 68, "ESPACE : SAUTER", 7)
        pyxel.text(45, 80, "MAINTENIR : SAUTER PLUS HAUT", 7)
        self.dessiner_bouton("RETOUR", 74, 105, 92, 18)

    def dessiner_dialogue_intro(self):
        lignes = LIGNES_DIALOGUE_INTRO[self.dialogue_intro]
        x, y, largeur, hauteur = 8, 96, LARGEUR_ECRAN - 16, 32
        pyxel.rect(x, y, largeur, hauteur, 0)
        pyxel.rectb(x, y, largeur, hauteur, 7)

        debut_y = y + (hauteur - len(lignes) * 8) // 2
        caracteres_restants = self.caracteres_dialogue
        for index, ligne in enumerate(lignes):
            texte_visible = ligne[:caracteres_restants]
            caracteres_restants -= len(texte_visible)
            pyxel.text(x + 6, debut_y + index * 8, texte_visible, 7)
        nombre_caracteres = sum(len(ligne) for ligne in lignes)
        if self.caracteres_dialogue >= nombre_caracteres:
            pyxel.text(x + largeur - 30, y + hauteur - 7, "ESPACE", 7)

    def draw(self):
        pyxel.cls(0)

        if self.etat == "menu":
            self.dessiner_menu()
            return
        if self.etat == "credits":
            self.dessiner_credits()
            return
        if self.etat == "touches":
            self.dessiner_touches()
            return

        # Afficher le fond déjà chargé, puis le niveau par-dessus.
        pyxel.blt(
            0, 0,
            BANQUE_FOND,
            0, 0,
            LARGEUR_ECRAN, HAUTEUR_ECRAN,
        )

        # Centrer la caméra sur le joueur sans dépasser les bords de la carte.
        camera_x = max(
            0,
            min(
                int(self.joueur.x + LARGEUR_JOUEUR / 2 - pyxel.width / 2),
                self.carte.largeur - pyxel.width,
            ),
        )
        camera_y = max(
            0,
            min(
                int(self.joueur.y) + HAUTEUR_JOUEUR // 2
                - pyxel.height // 2,
                self.carte.hauteur - pyxel.height,
            ),
        )

        # 1. Dessiner le niveau créé dans Tiled
        self.carte.dessiner(camera_x, camera_y)

        # 2. Dessiner le joueur par-dessus le niveau
        self.joueur.dessiner(camera_x, camera_y)

        # 3. Dessiner les calques Tiled suffixés par "_2" devant le joueur.
        self.carte.dessiner(camera_x, camera_y, devant=True)

        # 4. Afficher les FPS et les dimensions de la carte chargée
        pyxel.rect(2, 2, 43, 9, 0)
        affichage_fps = f"FPS: {self.fps}" if self.fps else "FPS: --"
        pyxel.text(4, 3, affichage_fps, 7)
        compteur = f"SKULLS: {self.gold_skulls}"
        compteur_x = pyxel.width - len(compteur) * 4 - 4
        pyxel.rect(compteur_x - 2, 2, len(compteur) * 4 + 4, 9, 0)
        pyxel.text(compteur_x, 4, compteur, 10)
        self.dessiner_fondu()
        if self.phase_intro == "dialogue":
            self.dessiner_dialogue_intro()


