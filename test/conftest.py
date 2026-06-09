"""Configuration pytest — sys.path, mocks pygame, fixtures partagées."""
import os
import sys
from unittest.mock import MagicMock

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_TEST_DIR)

# CWD = racine du projet (nécessaire pour utils/perm.json dans noise.py)
os.chdir(_PROJECT_ROOT)

# sys.path : racine projet ET dossier test (pour `from helpers import …`)
for _p in (_PROJECT_ROOT, _TEST_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Mock pygame AVANT tout import de module projet
_pygame_mock = MagicMock()
_pygame_mock.init.return_value = (1, 0)
_pygame_mock.font = MagicMock()
_pygame_mock.font.SysFont.return_value = MagicMock()
sys.modules.setdefault("pygame", _pygame_mock)

import pytest
from world.unit import Unit
from world.city import City
from helpers import MockMap, make_tile, make_linear_map, MockGameState
from world.unit import Soldier, Cavalry, Archer, Colon, Baby, Boat


@pytest.fixture(autouse=True)
def reset_global_counters():
    """Réinitialise les compteurs globaux avant chaque test."""
    Unit._unit_counter = 0
    City._next_id = 0
    yield


# --- Fixtures d'unités ---

@pytest.fixture
def soldier():
    return Soldier(tile_id=0, owner=0)


@pytest.fixture
def cavalry():
    return Cavalry(tile_id=0, owner=0)


@pytest.fixture
def archer():
    return Archer(tile_id=0, owner=0)


@pytest.fixture
def colon():
    return Colon(tile_id=0, owner=0)


@pytest.fixture
def baby():
    return Baby(tile_id=0, owner=0)


@pytest.fixture
def boat():
    return Boat(tile_id=0, owner=0)


# --- Fixtures de carte ---

@pytest.fixture
def five_tile_map():
    return make_linear_map(5)


@pytest.fixture
def mock_game_state(five_tile_map):
    return MockGameState(five_tile_map)
