"""
Configuration globale pytest et fixtures partagées.

Lancer les tests depuis la racine du projet :
    cd ~/proj_info
    pytest test/

Dépendances de test :
    pip install pytest scipy pygame-ce
"""
import os
import sys

#  1. Chemins absolus
_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_TEST_DIR)

#  2. CWD = racine du projet (noise.py utilise open("utils/perm.json"))
os.chdir(_PROJECT_ROOT)

#  3. sys.path : racine projet + dossier test
#     - _PROJECT_ROOT : permet `from world.xxx import ...`
#     - _TEST_DIR     : permet `from helpers import ...` depuis les sous-dossiers
for _p in (_PROJECT_ROOT, _TEST_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

#  4. Mock pygame AVANT tout import de module projet
# world/unit.py appelle pygame.init() et pygame.font.SysFont() au niveau module.
from unittest.mock import MagicMock
_pygame_mock = MagicMock()
_pygame_mock.init.return_value = (1, 0)
_pygame_mock.font = MagicMock()
_pygame_mock.font.SysFont.return_value = MagicMock()
sys.modules.setdefault("pygame", _pygame_mock)

#  5. Imports projet
import pytest
from world.biome import Biome
from world.resources import Resource
from world.tile import Tile
from world.unit import Unit, Soldier, Cavalry, Archer, Colon, Baby, Plane, Boat
from world.kingdom import Kingdom

# helpers.py centralise MockMap / make_tile / make_linear_map / MockGameState
from helpers import MockMap, make_tile, make_linear_map, MockGameState


#  Fixtures de réinitialisation (autouse)

@pytest.fixture(autouse=True)
def _reset_unit_counter():
    """Remet le compteur global d'ID d'unités à zéro avant chaque test."""
    Unit._unit_counter = 0
    yield


@pytest.fixture(autouse=True)
def _reset_city_id():
    """Remet le compteur global d'ID de villes à zéro avant chaque test."""
    from world.city import City
    City._next_id = 0
    yield


#  Fixtures de tuiles

@pytest.fixture
def plain_tile() -> Tile:
    return make_tile(0, biome=Biome.PLAIN)


@pytest.fixture
def water_tile() -> Tile:
    return make_tile(0, biome=Biome.WATER)


@pytest.fixture
def forest_tile() -> Tile:
    return make_tile(0, biome=Biome.FOREST)


@pytest.fixture
def mountain_tile() -> Tile:
    return make_tile(0, biome=Biome.MOUNTAIN)


@pytest.fixture
def desert_tile() -> Tile:
    return make_tile(0, biome=Biome.DESERT)


#  Fixtures d'unités

@pytest.fixture
def soldier() -> Soldier:
    return Soldier(tile_id=0, owner=0)


@pytest.fixture
def enemy_soldier() -> Soldier:
    return Soldier(tile_id=1, owner=1)


@pytest.fixture
def cavalry() -> Cavalry:
    return Cavalry(tile_id=0, owner=0)


@pytest.fixture
def archer() -> Archer:
    return Archer(tile_id=0, owner=0)


@pytest.fixture
def colon() -> Colon:
    return Colon(tile_id=0, owner=0)


@pytest.fixture
def boat() -> Boat:
    return Boat(tile_id=0, owner=0)


#  Fixtures de carte

@pytest.fixture
def five_tile_map() -> MockMap:
    """Chaîne linéaire de 5 tuiles : 0 ↔ 1 ↔ 2 ↔ 3 ↔ 4 (biome PLAIN)."""
    return make_linear_map(5)


@pytest.fixture
def mock_game_state(five_tile_map) -> MockGameState:
    return MockGameState(five_tile_map)
