from world.biome import Biome


class GameConfig:
    TILE_SIZE = 2
    TILE_AVG_AREA = 35
    HEIGHT = 250
    WIDTH = (HEIGHT * 16) // 9

    FPS = 60

    SCREEN_WIDTH = WIDTH * TILE_SIZE
    SCREEN_HEIGHT = HEIGHT * TILE_SIZE

    LOG_MAP_GENERATION = True

    BIOME_COLORS = {
        Biome.BLANK: (0, 0, 0),
        Biome.WATER: (50, 80, 200),
        Biome.PLAIN: (120, 200, 100),
        Biome.FOREST: (30, 120, 30),
        Biome.MOUNTAIN: (120, 120, 120),
        Biome.DESERT: (194, 178, 128),
    }

    BUTTON_WIDTH = 150
    BUTTON_HEIGHT = 40
    BUTTON_X = 10
    BUTTON_Y = 50
    BUTTON_COLOR = (100, 100, 200)
    BUTTON_HOVER_COLOR = (150, 150, 255)
    BUTTON_ACTIVE_COLOR = (255, 100, 100)

    SIDEBAR_WIDTH = 210  # largeur de la barre latérale gauche
    STATUS_H = 52  # hauteur barre de statut bas

    RESOURCE_BASE_SCALE = 3
