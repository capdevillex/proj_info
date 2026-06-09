"""Helpers partagés entre tous les fichiers de test."""
import os
import sys

# S'assurer que le projet racine est dans sys.path
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_TEST_DIR)
os.chdir(_PROJECT_ROOT)
for _p in (_PROJECT_ROOT, _TEST_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Mock pygame avant tout import de modules projet
from unittest.mock import MagicMock as _MagicMock
_pg = _MagicMock()
_pg.init.return_value = (1, 0)
_pg.font = _MagicMock()
_pg.font.SysFont.return_value = _MagicMock()
sys.modules.setdefault("pygame", _pg)

from world.biome import Biome
from world.resources import Resource
from world.tile import Tile


class MockMap:
    """Substitut léger à Map — évite la génération procédurale complète."""

    def __init__(self, tiles=None):
        self.tiles = tiles or {}


def make_tile(
    id_: int,
    cells=None,
    biome: Biome = Biome.PLAIN,
    resource: Resource = Resource.NONE,
) -> Tile:
    if cells is None:
        cells = [(id_ * 10, 0), (id_ * 10 + 1, 0)]
    return Tile(id_, cells, biome, resource)


def make_linear_map(n: int, biome: Biome = Biome.PLAIN) -> MockMap:
    """Crée n tuiles en chaîne linéaire : 0 ↔ 1 ↔ 2 ↔ … ↔ n-1."""
    tiles = {i: make_tile(i, biome=biome) for i in range(n)}
    for i in range(n):
        if i > 0:
            tiles[i].neighbors.add(i - 1)
        if i < n - 1:
            tiles[i].neighbors.add(i + 1)
    return MockMap(tiles)


class MockGameState:
    """Substitut minimal à GameState pour les tests de mouvement et de combat."""

    def __init__(self, map_: MockMap):
        self.map = map_
        self.units = []
        self.cities = []
        self.current_player = 0
        self.player_resources = {
            0: {"food": 0, "wood": 0, "stone": 0, "iron": 0, "gold": 0}
        }
        self.use_ti = False
        self.discovered = (1 << 256) - 1
        self.use_fow = False
