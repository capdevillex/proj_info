from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from core.game_state import GameState
    from core.game_engine import GameEngine
    from world.unit import Unit
    from world.city import City


class BaseAI(ABC):
    """Interface abstraite pour toutes les IA de royaumes ennemis.

    Chaque IA contrôle un unique royaume identifié par kingdom_id.
    L'arbre de décision pondéré sera implémenté dans les sous-classes concrètes
    en utilisant self.params pour calibrer les comportements.

    Comportements prévus (à implémenter dans les sous-classes) :
      - Déplacer les unités vers le joueur si visibles
      - Attaquer les unités adjacentes ennemies
      - Explorer les tuiles inconnues si rien de mieux à faire
    """

    def __init__(self, kingdom_id: int, params: dict):
        """
        Args:
            kingdom_id: ID du royaume contrôlé par cette IA.
            params: Poids de décision (ex. {"aggression": 0.8, "exploration": 0.5}).
        """
        self.kingdom_id = kingdom_id
        self.params = params

    @abstractmethod
    def play_turn(self, state: "GameState", engine: "GameEngine") -> None:
        """Exécute le tour complet de l'IA.

        Appelé une fois par round, après le tour du joueur humain.
        L'implémentation doit utiliser engine.move_unit() et engine.attack_unit()
        pour agir ; elle ne doit PAS modifier state directement.
        """
        ...

    # Helpers de lecture (n'appellent pas engine, lecture seule)
    def get_own_units(self, state: "GameState") -> List["Unit"]:
        return [u for u in state.units if u.owner == self.kingdom_id]

    def get_own_cities(self, state: "GameState") -> List["City"]:
        return [c for c in state.cities if c.owner == self.kingdom_id]

    def get_enemy_units(self, state: "GameState") -> List["Unit"]:
        """Retourne toutes les unités n'appartenant pas à ce royaume."""
        return [u for u in state.units if u.owner != self.kingdom_id]

    def get_visible_tiles(self, state: "GameState") -> int:
        """Retourne le bitmask de visibilité propre à ce royaume."""
        return state.get_kingdom_visibility(self.kingdom_id)

    def is_tile_visible(self, state: "GameState", tile_id: int) -> bool:
        return bool(self.get_visible_tiles(state) & (1 << tile_id))
