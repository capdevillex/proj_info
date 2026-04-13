"""
Visualiseur interactif de bruit de Perlin

Permet de modifier en temps réel les paramètres de génération du bruit de Perlin
et de visualiser le résultat.

Contrôles:
    - Flèches HAUT/BAS : Modifier les octaves (1-8)
    - Q/A : Modifier la persistance (0.1-1.0)
    - W/S : Modifier la lacunarité (1.5-3.0)
    - E/D : Modifier l'échelle (10-200)
    - R/F : Modifier la seed (0-255)
    - ESPACE : Régénérer avec une seed aléatoire
    - ÉCHAP : Quitter
"""

import pygame
import random
from utils.noise import perlin_noise


# Configuration de la fenêtre
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
NOISE_WIDTH = 800
NOISE_HEIGHT = 800
PANEL_WIDTH = WINDOW_WIDTH - NOISE_WIDTH

# Taille d'un "pixel" de bruit (affichage agrandi)
PIXEL_SIZE = 4
NOISE_GRID_WIDTH = NOISE_WIDTH // PIXEL_SIZE
NOISE_GRID_HEIGHT = NOISE_HEIGHT // PIXEL_SIZE

# Couleurs
BG_COLOR = (20, 20, 30)
PANEL_BG = (30, 30, 40)
TEXT_COLOR = (220, 220, 220)
HIGHLIGHT_COLOR = (100, 150, 255)
BUTTON_COLOR = (50, 50, 70)
BUTTON_HOVER = (70, 70, 90)


class PerlinVisualizer:
    """Visualiseur interactif de bruit de Perlin"""

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("Perlin Noise Visualizer")

        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 16)
        self.title_font = pygame.font.SysFont("monospace", 20, bold=True)

        # Paramètres du bruit de Perlin
        self.octaves = 4
        self.persistence = 0.5
        self.lacunarity = 2.0
        self.scale = 50.0
        self.seed = 0

        # Surface pour le rendu du bruit
        self.noise_surface = pygame.Surface((NOISE_WIDTH, NOISE_HEIGHT))
        self.needs_update = True

        # État de l'interface
        self.running = True

    def update_noise(self):
        """Génère et affiche le bruit de Perlin avec les paramètres actuels"""
        # Générer le bruit sur une grille réduite
        for grid_y in range(NOISE_GRID_HEIGHT):
            for grid_x in range(NOISE_GRID_WIDTH):
                # Calculer la valeur du bruit pour cette cellule de la grille
                noise_val = perlin_noise(
                    grid_x / (self.scale / PIXEL_SIZE),
                    grid_y / (self.scale / PIXEL_SIZE),
                    octaves=self.octaves,
                    persistence=self.persistence,
                    lacunarity=self.lacunarity,
                    base=self.seed,
                )

                # Normaliser entre 0 et 255
                color_val = int((noise_val + 1) * 127.5)
                color_val = max(0, min(255, color_val))
                color = (color_val, color_val, color_val)

                # Dessiner un carré de PIXEL_SIZE x PIXEL_SIZE pixels
                pygame.draw.rect(
                    self.noise_surface,
                    color,
                    (grid_x * PIXEL_SIZE, grid_y * PIXEL_SIZE, PIXEL_SIZE, PIXEL_SIZE),
                )

        self.needs_update = False

    def draw_panel(self):
        """Dessine le panneau de contrôle avec les paramètres"""
        panel_x = NOISE_WIDTH

        # Fond du panneau
        pygame.draw.rect(self.screen, PANEL_BG, (panel_x, 0, PANEL_WIDTH, WINDOW_HEIGHT))

        # Titre
        title = self.title_font.render("PERLIN NOISE", True, HIGHLIGHT_COLOR)
        self.screen.blit(title, (panel_x + 20, 20))

        # Paramètres
        y_offset = 80
        line_height = 35

        params = [
            ("OCTAVES", self.octaves, "↑/↓", f"{self.octaves}"),
            ("PERSISTENCE", self.persistence, "Q/D", f"{self.persistence:.2f}"),
            ("LACUNARITY", self.lacunarity, "Z/S", f"{self.lacunarity:.2f}"),
            ("SCALE", self.scale, "A/E", f"{self.scale:.1f}"),
            ("SEED", self.seed, "R/F", f"{self.seed}"),
        ]

        for label, value, keys, display in params:
            # Label
            label_text = self.font.render(label, True, TEXT_COLOR)
            self.screen.blit(label_text, (panel_x + 20, y_offset))

            # Valeur
            value_text = self.font.render(display, True, HIGHLIGHT_COLOR)
            self.screen.blit(value_text, (panel_x + 200, y_offset))

            # Touches
            keys_text = self.font.render(f"[{keys}]", True, (150, 150, 150))
            self.screen.blit(keys_text, (panel_x + 20, y_offset + 18))

            y_offset += line_height + 15

        # Instructions supplémentaires
        y_offset += 30
        instructions = [
            "ESPACE : Seed aléatoire",
            "ÉCHAP : Quitter",
        ]

        for instruction in instructions:
            text = self.font.render(instruction, True, (180, 180, 180))
            self.screen.blit(text, (panel_x + 20, y_offset))
            y_offset += 25

        # Informations sur le bruit
        y_offset += 30
        info_title = self.title_font.render("INFO", True, HIGHLIGHT_COLOR)
        self.screen.blit(info_title, (panel_x + 20, y_offset))
        y_offset += 35

        info_lines = [
            f"Résolution: {NOISE_WIDTH}x{NOISE_HEIGHT}",
            f"Grille: {NOISE_GRID_WIDTH}x{NOISE_GRID_HEIGHT}",
            f"Pixel size: {PIXEL_SIZE}x{PIXEL_SIZE}",
            f"Range: [-1, 1]",
            f"Normalized: [0, 255]",
        ]

        for line in info_lines:
            text = self.font.render(line, True, (150, 150, 150))
            self.screen.blit(text, (panel_x + 20, y_offset))
            y_offset += 22

    def handle_input(self):
        """Gère les entrées clavier"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            if event.type == pygame.KEYDOWN:
                # Quitter
                if event.key == pygame.K_ESCAPE:
                    self.running = False

                # Octaves (↑/↓)
                elif event.key == pygame.K_UP:
                    self.octaves = min(8, self.octaves + 1)
                    self.needs_update = True
                elif event.key == pygame.K_DOWN:
                    self.octaves = max(1, self.octaves - 1)
                    self.needs_update = True

                # Persistence (Q/D)
                elif event.key == pygame.K_q:
                    self.persistence = min(1.0, self.persistence + 0.05)
                    self.needs_update = True
                elif event.key == pygame.K_d:
                    self.persistence = max(0.1, self.persistence - 0.05)
                    self.needs_update = True

                # Lacunarité (Z/S)
                elif event.key == pygame.K_z:
                    self.lacunarity = min(3.0, self.lacunarity + 0.1)
                    self.needs_update = True
                elif event.key == pygame.K_s:
                    self.lacunarity = max(1.5, self.lacunarity - 0.1)
                    self.needs_update = True

                # Scale (A/E)
                elif event.key == pygame.K_a:
                    self.scale = min(200.0, self.scale + 5.0)
                    self.needs_update = True
                elif event.key == pygame.K_e:
                    self.scale = max(10.0, self.scale - 5.0)
                    self.needs_update = True

                # Seed (R/F)
                elif event.key == pygame.K_r:
                    self.seed = (self.seed + 1) % 256
                    self.needs_update = True
                elif event.key == pygame.K_f:
                    self.seed = (self.seed - 1) % 256
                    self.needs_update = True

                # Seed aléatoire (ESPACE)
                elif event.key == pygame.K_SPACE:
                    self.seed = random.randint(0, 255)
                    self.needs_update = True
                    print(f"Nouvelle seed: {self.seed}")

    def run(self):
        """Boucle principale"""
        print("Visualiseur de bruit de Perlin démarré")
        print("Utilisez les touches pour modifier les paramètres")

        while self.running:
            self.handle_input()

            # Mettre à jour le bruit si nécessaire
            if self.needs_update:
                print(
                    f"Génération du bruit... (octaves={self.octaves}, persistence={self.persistence:.2f}, lacunarity={self.lacunarity:.2f}, scale={self.scale:.1f}, seed={self.seed})"
                )
                self.update_noise()

            # Rendu
            self.screen.fill(BG_COLOR)
            self.screen.blit(self.noise_surface, (0, 0))
            self.draw_panel()

            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        print("Visualiseur fermé")


def main():
    visualizer = PerlinVisualizer()
    visualizer.run()


if __name__ == "__main__":
    main()
