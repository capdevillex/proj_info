from typing import List, Dict, Set, Tuple, Optional, Union, Any

from core.game_state import GameState

from core.systems import Movement, Combat, Economy, Visibility
from world.unit import Unit
from world.map import Map


class GameEngine:
    def __init__(self, game_state: GameState):
        self.state = game_state

        self.movement = Movement()
        self.combat = Combat()
        self.economy = Economy()
        self.visibility = Visibility()

    def move_unit(self, unit_id, target_tile):
        self.movement.move(self.state, unit_id, target_tile)
        self.visibility.update(self.state)

    def attack(self, attacker_id, defender_id):
        self.combat.resolve(self.state, attacker_id, defender_id)

    def end_turn(self):
        self.economy.update(self.state)
        self.state.turn += 1

    def spawn_unit(self, unit_type, tile_id):
        """Place une nouvelle unité du type spécifié sur la tuile donnée."""
        new_unit = Unit(unit_type, tile_id, owner=self.state.current_player)
        self.state.units.append(new_unit)
        self.visibility.update(self.state)
