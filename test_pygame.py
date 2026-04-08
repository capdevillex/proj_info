import pygame
import sys

pygame.init()

# --- Configuration Responsive ---
# On définit d'abord la taille de la fenêtre "cible"
TAILLE_FENETRE = 800  
# On définit le nombre de cases (ex: 50 pour une grille de 50x50)
NOMBRE_CASES = 50 

# On calcule dynamiquement la taille d'une case
# Le $inline$ de la taille est : TAILLE\_FENETRE / NOMBRE\_CASES
TAILLE_CASE = TAILLE_FENETRE / NOMBRE_CASES

# Couleurs
BLANC = (255, 255, 255)
NOIR = (0, 0, 0)
BLEU = (0, 120, 255)
GRIS_GRILLE = (40, 40, 40)

ecran = pygame.display.set_mode((TAILLE_FENETRE, TAILLE_FENETRE))
pygame.display.set_caption(f"Grille Responsive : {NOMBRE_CASES}x{NOMBRE_CASES}")

# Création de la matrice (0 = vide, 1 = cliqué)
grille_donnees = [[0 for _ in range(NOMBRE_CASES)] for _ in range(NOMBRE_CASES)]

horloge = pygame.time.Clock()

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                pos_x, pos_y = pygame.mouse.get_pos()
                
                # Conversion inverse : pixels -> index de la grille
                colonne = int(pos_x // TAILLE_CASE)
                ligne = int(pos_y // TAILLE_CASE)
                
                if 0 <= ligne < NOMBRE_CASES and 0 <= colonne < NOMBRE_CASES:
                    grille_donnees[ligne][colonne] = 1 - grille_donnees[ligne][colonne]

    ecran.fill(NOIR)

    # Dessin de la grille
    for ligne in range(NOMBRE_CASES):
        for colonne in range(NOMBRE_CASES):
            # On utilise des flottants pour les calculs de position pour éviter les décalages
            rect = (colonne * TAILLE_CASE, ligne * TAILLE_CASE, TAILLE_CASE, TAILLE_CASE)
            
            if grille_donnees[ligne][colonne] == 1:
                pygame.draw.rect(ecran, BLEU, rect)
            
            # On ne dessine les lignes que si les cases sont assez grandes pour que ce soit lisible
            if TAILLE_CASE > 2:
                pygame.draw.rect(ecran, GRIS_GRILLE, rect, 1)

    pygame.display.flip()
    horloge.tick(60)