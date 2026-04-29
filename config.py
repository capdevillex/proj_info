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
    BORDER_STRENGTH = 2.75
    OCEANIC_COEFF = 1.5  # /!\ ++ = - d'eau
    OCEANIC_OFFSET = 0.1
    DESERT_HEAT_THRESHOLD = 0.15
    # Taille minimale d'un cluster d'eau (en nombre de tuiles) pour être conservé. Les groupes connexes
    # de tuiles d'eau dont la taille est <= à cette valeur seront convertis en biome terrestre.
    MIN_WATER_CLUSTER_SIZE = 2
    # Taille minimale d'une masse d'eau pour tenter de la relier à une voisine.
    WATER_CONNECT_MIN_SIZE = 8
    # Distance maximale (en sauts de tuile) entre deux masses d'eau pour les relier.
    WATER_BRIDGE_MAX_HOPS = 3
    # Coefficient de fusion des tuiles d'eau proches en super-tuiles plus grandes pour améliorer la jouabilité.
    WATER_TILE_SIZE_COEFF = 8

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
    CONSTRUCTION_MENU_WIDTH = 200
    CONSTRUCTION_MENU_ITEM_H = 40
    CONSTRUCTION_MENU_PADDING = 10

    RESOURCE_BASE_SCALE = 3

    CITY_MIN_TURN_EXTENTION_AVAILABLE = [3, 5, 8, 13, 21, 34, 53, 89]
    CITY_EXTENSION_RADIUS = 3  # max de distance entre la province fondatrice et la nouvelle province pour pouvoir l'étendre
    CITY_EXTENSION_FOOD_POP_MIN_RATION = (
        1.25  # ration minimum de nourriture par habitant pour pouvoir étendre une ville
    )
