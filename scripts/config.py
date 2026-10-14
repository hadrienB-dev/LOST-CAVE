"""Constantes de configuration du jeu."""

LARGEUR_ECRAN = 240
HAUTEUR_ECRAN = 135
TITRE = "LOST CAVE"

TAILLE_TILE = 32
LARGEUR_JOUEUR = 20
HAUTEUR_JOUEUR = 32
Y_DEPART = 192
DEBUT_SPRITESHEET_SAUT = LARGEUR_JOUEUR * 4

VITESSE_DEPLACEMENT = 1
VITESSE_ANIMATION = 15
TOLERANCE_SAUT_FRAMES = 6
COULEUR_TRANSPARENCE = 8
DUREE_FONDU_FRAMES = 24
FRAMES_PAR_CARACTERE_DIALOGUE = 2
LIGNES_DIALOGUE_INTRO = (
    ("Qu'est-ce que je fais ici ?",),
    (
        "Je ferais mieux de sortir de cet",
        "endroit au plus vite...",
    ),
    ("J'ai un mauvais pressentiment.",),
)

GRAVITE = 0.35
VITESSE_SAUT = -6.36
FORCE_SAUT_MAINTENU = 0.19
DUREE_SAUT_MAX_FRAMES = 12
VOLUME_SAUT = 0.04

# Banques d'images Pyxel
BANQUE_JOUEUR = 0
BANQUE_FOND = 1
BANQUE_SOL = 0
BANQUE_TITRE = 0
ORIGINE_Y_FOND_TITRE = 64
ORIGINE_Y_SOL = 224

# Fichiers de ressources
FICHIER_RESSOURCES = "assets/pyxel/theme.pyxres"
FICHIER_SPRITESHEET = "assets/sprites/spritesheet_80x64.png"
FICHIER_SPRITESHEET_SAUT = "assets/sprites/spritesheet_jump.png"
FICHIER_FOND = "assets/sprites/level_background_240x135.png"
FICHIER_FOND_TITRE = "assets/sprites/title_screen_background.png"
FICHIER_FOND_INTRO = "assets/sprites/background_intro.png"
FICHIER_SOL = "assets/sprites/acide.png"
FICHIER_PORTRAIT_HERO = "assets/sprites/hero_mugshot.png"
FICHIER_MUSIQUE = "assets/audio/lost_cave.ogg"
FICHIER_MUSIQUE_TITRE = "assets/audio/title_screen.ogg"
FICHIER_SFX_DIALOGUE = "assets/audio/text_loop_speech.ogg"
FICHIER_SAUT = "assets/audio/jump.ogg"
FICHIER_FIN_SAUT = "assets/audio/jump_end.ogg"
FICHIER_COLLECTE_CRANE = "assets/audio/skull_collect.ogg"

# ============================================================
# JOUEUR
# ============================================================
