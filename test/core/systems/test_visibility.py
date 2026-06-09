"""Tests unitaires pour core/systems/visibility.py"""
import pytest
from unittest.mock import MagicMock
from world.unit import Soldier, Archer
from core.systems.visibility import Visibility
from helpers import make_tile, make_linear_map, MockMap, MockGameState


@pytest.fixture
def visibility_system(mock_game_state):
    return Visibility(mock_game_state)


class TestVisibilityUpdate:
    def test_update_calls_update_fow(self, mock_game_state):
        vis = Visibility(mock_game_state)
        mock_game_state.update_fow = MagicMock()
        vis.update(mock_game_state)
        mock_game_state.update_fow.assert_called_once()


class TestCalculateVisibleTiles:
    def test_includes_own_tile(self, visibility_system, five_tile_map):
        u = Soldier(tile_id=2, owner=0)
        visible = visibility_system.calculate_visible_tiles(u, five_tile_map)
        assert 2 in visible

    def test_includes_neighbor_cells(self, visibility_system):
        t0 = make_tile(0, cells=[(0, 0), (1, 0)])
        t1 = make_tile(1, cells=[(10, 0), (11, 0)])
        t0.neighbors.add(1)
        t1.neighbors.add(0)
        map_ = MockMap({0: t0, 1: t1})
        vis = Visibility(MockGameState(map_))
        u = Soldier(tile_id=0, owner=0)
        visible = vis.calculate_visible_tiles(u, map_)
        # La tuile voisine (1) a des cells qui devraient être visibles
        for cell in t1.cells:
            assert cell in visible

    def test_isolated_tile_sees_only_self(self, visibility_system):
        isolated = make_tile(99, cells=[(50, 50)])
        map_ = MockMap({99: isolated})
        vis = Visibility(MockGameState(map_))
        u = Soldier(tile_id=99, owner=0)
        visible = vis.calculate_visible_tiles(u, map_)
        assert 99 in visible
