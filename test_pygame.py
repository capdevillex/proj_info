import pygame
import sys

# 1. Initialisation de Pygame (fonctionne avec pygame-ce)
pygame.init()

# --- Configuration ---
# Dimensions de la grille
NOMBRE_CASES = 10
TAILLE_CASE = 40  # pixels

# Calcul de la taille de la fenêtre
LARGEUR_ECRAN = NOMBRE_CASES * TAILLE_CASE
HAUTEUR_ECRAN = NOMBRE_CASES * TAILLE_CASE

# Couleurs (R, G, B)
BLANC = (255, 255, 255)
NOIR = (0, 0, 0)
VERT = (0, 200, 0)
GRIS_GRILLE = (100, 100, 100)

# 2. Création de la fenêtre
ecran = pygame.display.set_mode((LARGEUR_ECRAN, HAUTEUR_ECRAN))
pygame.display.set_caption("Grille Cliquable Simple")

# 3. Création des données de la grille (0 = Noir, 1 = Vert)
# Une liste de listes (matrice) initialisée à 0
grille_donnees = []
for ligne in range(NOMBRE_CASES):
    grille_donnees.append([0] * NOMBRE_CASES)

# Pour contrôler la vitesse de rafraîchissement
horloge = pygame.time.Clock()

# --- Boucle principale du jeu ---
while True:
    # 4. Gestion des événements (clavier/souris)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
            
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Si on clique avec le bouton gauche
            if event.button == 1:
                # Obtenir la position de la souris
                pos_x, pos_y = pygame.mouse.get_pos()
                
                # Convertir les pixels en coordonnées de grille (colonne, ligne)
                colonne = pos_x // TAILLE_CASE
                ligne = pos_y // TAILLE_CASE
                
                # Vérifier qu'on est bien dans la grille (sécurité)
                if 0 <= ligne < NOMBRE_CASES and 0 <= colonne < NOMBRE_CASES:
                    # Inverser l'état de la case (0 devient 1, 1 devient 0)
                    if grille_donnees[ligne][colonne] == 0:
                        grille_donnees[ligne][colonne] = 1
                    else:
                        grille_donnees[ligne][colonne] = 0

    # 5. Dessin
    ecran.fill(BLANC)  # Effacer l'écran avec un fond blanc

    # Dessiner les cases et les lignes de la grille
    for ligne in range(NOMBRE_CASES):
        for colonne in range(NOMBRE_CASES):
            # Calculer la position x, y en pixels du coin haut gauche de la case
            x = colonne * TAILLE_CASE
            y = ligne * TAILLE_CASE
            
            # Déterminer la couleur de remplissage
            couleur_remplissage = NOIR
            if grille_donnees[ligne][colonne] == 1:
                couleur_remplissage = VERT
                
            # Dessiner le rectangle plein de la case
            pygame.draw.rect(ecran, couleur_remplissage, (x, y, TAILLE_CASE, TAILLE_CASE))
            
            # Dessiner le contour gris de la case (la grille)
            pygame.draw.rect(ecran, GRIS_GRILLE, (x, y, TAILLE_CASE, TAILLE_CASE), 1)

    # 6. Mettre à jour l'affichage
    pygame.display.flip()
    
    # Limiter à 60 images par seconde (pour ne pas surcharger le processeur)
    horloge.tick(60)    