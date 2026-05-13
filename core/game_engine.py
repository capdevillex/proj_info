from typing import Dict, Optional

from core.game_state import GameState, TurnPhase
from core.systems import Movement, Combat, Economy, Visibility
from core.ai.base_ai import BaseAI
from world.unit import Unit, UnitType, UNIT_CLASS_MAP
from world.construction import Farm, Mine, Road, Scierie
from world.city import City
from world.biome import Biome
from config import GameConfig as gc
import random


class GameEngine:
    """
    Moteur de jeu central pour le 4X.

    Gère toutes les interactions entre les systèmes (mouvement, combat, économie, visibilité)
    et maintient la cohérence de l'état du jeu.

    Cycle de tour :
        1. Tour joueur  → end_turn() appelé depuis l'UI
        2. Tours IA     → _run_ai_turns() (une passe par royaume IA, dans l'ordre)
        3. Fin de round → _end_round() (économie, reset mouvement, compteur, FOW)
    """

    def __init__(self, game_state: GameState):
        self.state = game_state

        # Systèmes de jeu
        self.movement = Movement  # Utiliser le système centralisé
        self.combat = Combat()
        self.economy = Economy()
        self.visibility = Visibility(self.state)

        # Contrôleurs IA enregistrés : kingdom_id → BaseAI
        self._ai_controllers: Dict[int, BaseAI] = {}

        # Flag pour forcer une mise à jour UI après certaines actions
        self.needs_ui_update = False

    @property
    def input_locked(self) -> bool:
        """True pendant les tours IA : l'UI doit ignorer toute entrée joueur."""
        return self.state.phase == TurnPhase.AI_TURN

    # Gestion des royaumes / IA
    def register_ai(self, ai: BaseAI) -> None:
        """Associe un contrôleur IA à un royaume.

        Doit être appelé avant la boucle de jeu. Le royaume correspondant doit
        déjà exister dans state.kingdoms.

        Args:
            ai: Instance concrète de BaseAI pour le royaume ai.kingdom_id.
        """
        kingdom = self.state.get_kingdom(ai.kingdom_id)
        if kingdom is None:
            raise ValueError(f"Royaume {ai.kingdom_id} inconnu — ajouter via state.add_kingdom() d'abord")
        if not kingdom.is_ai:
            raise ValueError(f"Le royaume {ai.kingdom_id} n'est pas marqué is_ai=True")
        self._ai_controllers[ai.kingdom_id] = ai
        print(f"[IA] Contrôleur enregistré pour '{kingdom.name}' (id={ai.kingdom_id})")

    #  Gestion des unités
    def spawn_unit(self, unit_type: UnitType, tile_id: int, owner: int = 0) -> Optional[Unit]:
        """Place une nouvelle unité du type spécifié sur la tuile donnée."""
        tile = self.state.map.tiles.get(tile_id)

        if not tile:
            print(f"❌ Tuile {tile_id} inexistante")
            return None

        if tile.has_units():
            print(f"❌ La tuile {tile_id} a déjà une unité")
            return None

        unit_class = UNIT_CLASS_MAP.get(unit_type)
        if not unit_class:
            print(f"❌ Type d'unité inconnu : {unit_type}")
            return None

        if tile.biome == Biome.WATER and not unit_class.WATER_AFFINITY:
            print(f"❌ Impossible de placer une unité terrestre sur l'eau (tuile {tile_id})")
            return None

        new_unit = unit_class(tile_id=tile_id, owner=owner)
        tile.add_unit(new_unit)
        self.state.units.append(new_unit)

        self.visibility.update(self.state)
        self.state.update_fow()

        print(f"✅ Unité {unit_type.name} numéro {new_unit.id} créée sur tuile {tile_id} (owner={owner})")
        return new_unit

    def move_unit(self, unit: Unit, target_tile_id: int) -> bool:
        """Déplace une unité vers une tuile cible.
        Args:
            unit: L'unité à déplacer
            target_tile_id: ID de la tuile de destination

        Returns:
            True si le mouvement a réussi, False sinon
        """
        # Utiliser le système centralisé
        success = self.movement.execute_move(self.state, unit, target_tile_id)
        if success:
            # Mettre à jour la visibilité après le mouvement
            self.visibility.update(self.state)
            self.state.update_fow()
        return success

    def remove_unit(self, unit: Unit) -> bool:
        """
        Retire une unité du jeu (mort, destruction, etc.).

        Args:
            unit: L'unité à retirer

        Returns:
            True si l'unité a été retirée, False sinon
        """
        # Retirer de la tuile
        tile = self.state.map.tiles.get(unit.tile_id)
        if tile:
            tile.remove_unit(unit)

        # Retirer de la liste des unités
        if unit in self.state.units:
            self.state.units.remove(unit)
            self.visibility.update(self.state)
            self.state.update_fow()
            print(f"✅ Unité {unit.id} retirée du jeu")
            return True
        return False

    #  Gestion du combat
    def attack_unit(self, attacker: Unit, target_tile_id: int) -> dict:
        """
        Attaque une unité sur une tuile cible.
        Délègue toute la logique à Combat, ne gère que les effets de bord.
        Retourne le dict complet : success, damage, defender, defender_killed.
        """
        result = self.combat.execute_attack(self.state, attacker, target_tile_id)

        if result["defender_killed"]:
            self.remove_unit(result["defender"])  # Effet de bord : retirer l'unité du jeu
            # (remove_unit met déjà à jour la visibilité)

        return result

    # ========== GESTION DES TOURS ==========

    def end_turn(self):
        """
        Termine le tour actuel et prépare le suivant.

        Actions effectuées :
        - Mise à jour de l'économie (ressources, entretien)
        - Réinitialisation des mouvements des unités
        - Incrémentation du compteur de tours
        - Mise à jour de la visibilité
        """
        print(f"\n{'='*50}")
        print(f"Fin du tour {self.state.turn}")
        print(f"{'='*50}")

        # Mettre à jour l'économie
        self.economy.update(self.state)

        # Réinitialiser le mouvement de toutes les unités
        for unit in self.state.units:
            unit.reset_movement()

        # Incrémenter le tour
        self.state.turn += 1

        # update des villes
        for city in self.state.cities:
            city.age += 1
            if city.age in gc.CITY_MIN_TURN_EXTENTION_AVAILABLE:
                print(f"La ville '{city.name}' peut être étendue (âge {city.age})")
                city.expend_territory(self.state)
                self.needs_ui_update = True

        # Mettre à jour la visibilité
        self.visibility.update(self.state)
        self.state.update_fow()

        print(f"\n{'='*50}")
        print(f"Début du tour {self.state.turn}")
        print(f"{'='*50}\n")

    # Gestion des villes

    def found_city(self, colon_unit: Unit, city_name: Optional[str] = None) -> bool:
        """
        Fonde une ville à l'emplacement d'un colon.

        Args:
            colon_unit: L'unité colon qui fonde la ville
            city_name: Nom de la ville (optionnel, généré automatiquement si None)

        Returns:
            True si la ville a été fondée, False sinon
        """
        # Vérifier que c'est bien un colon
        if colon_unit.unit_type != UnitType.COLON:
            print(f"❌ Seul un colon peut fonder une ville")
            return False

        # Vérifier que la tuile existe
        tile = self.state.map.tiles.get(colon_unit.tile_id)
        if not tile:
            print(f"❌ Tuile {colon_unit.tile_id} inexistante")
            return False

        # Vérifier qu'il n'y a pas déjà une ville sur cette tuile
        if self.state.get_city_at_tile(colon_unit.tile_id):
            print(f"❌ Il y a déjà une ville sur cette tuile")
            return False

        # Vérifier que la tuile n'est pas de l'eau
        if tile.is_water():
            print(f"❌ Impossible de fonder une ville sur l'eau")
            return False

        # Générer un nom de ville si non fourni
        if city_name is None:
            city_name = self._generate_city_name(colon_unit.owner)

        new_city = City(
            name=city_name,
            owner=colon_unit.owner,
            center_tile_id=colon_unit.tile_id,
            state=self.state,
        )
        self.state.add_city(new_city)

        # Calculer la production initiale
        new_city.calculate_production(self.state.map)

        # Retirer le colon du jeu
        self.remove_unit(colon_unit)

        print(f"✅ Ville '{city_name}' fondée sur la tuile {colon_unit.tile_id} par le royaume {colon_unit.owner}")
        return True

    def _generate_city_name(self, owner: int) -> str:
        """
        Génère un nom de ville automatiquement.

        Args:
            owner: ID du joueur propriétaire

        Returns:
            Nom de la ville
        """
        # Listes de noms de villes, je dois avouer avoir une inspiration limitée
        city_names = [
            "Nova", "Bourg Palette", "Arcadia", "Zenith", "Aurora",
            "Elysium", "Olympus", "Volucité", "Atlantis", "Avalon",
            "Carmin-sur-mer", "Kaamelott", "Eden", "Relifac-le-Haut",
            "Utopia", "Paradis", "Lavanville", "Harmonie", "Prospérité",
            "Liberté", "Féli-Cité", "Espoir", "Lumière",
            "Auffrac-les-Congères", "Victorville", "Cap-de-ville"
            "Gloire", "Honneur",
        ]
        # Récupérer les noms déjà utilisés
        used_names = {city.name for city in self.state.cities if city.owner == owner}
        # Trouver les noms disponibles
        available_names = [name for name in city_names if name not in used_names]

        if available_names:                # Piocher un nom aléatoire parmi les disponibles
            return random.choice(available_names)

        # Si tous les noms sont pris, ajouter un numéro
        base_name = city_names[0]
        counter = 1
        while f"{base_name} {counter}" in used_names:
            counter += 1
        return f"{base_name} {counter}"

    # Gestion du terrain / placement initial
    def get_corner_tile(self, corner: str) -> Optional[int]:
        """Retourne l'ID de la tuile non-occupée la plus proche d'un coin.

        Coins acceptés : "top_left", "bottom_right", "top_right", "bottom_left".
        """
        tiles = list(self.state.map.tiles.values())
        corner_keys = {
            "top_left":     (lambda t: t.center[0] + t.center[1], False),
            "bottom_right": (lambda t: t.center[0] + t.center[1], True),
            "top_right":    (lambda t: t.center[0] - t.center[1], True),
            "bottom_left":  (lambda t: t.center[0] - t.center[1], False),
        }
        key_fn, reverse = corner_keys.get(corner, corner_keys["top_left"])
        candidates = sorted(tiles, key=key_fn, reverse=reverse)
        for tile in candidates:
            if not tile.has_units():
                return tile.id

        return None

    def setup_start_units(self) -> None:
        """Fait spawner un colon de départ pour chaque royaume enregistré.

        L'ordre des coins suit l'ordre dans turn_order :
          index 0 → top_left, 1 → bottom_right, 2 → top_right, 3 → bottom_left, ...
        """
        corners = ["top_left", "bottom_right", "top_right", "bottom_left"]
        for i, kingdom_id in enumerate(self.state.turn_order):
            corner = corners[i % len(corners)]
            tile_id = self.get_corner_tile(corner)
            if tile_id is not None:
                unit = self.spawn_unit(UnitType.COLON, tile_id, owner=kingdom_id)
                if unit and kingdom_id == self.state.current_player:
                    unit.upkeep_cost = 0  # colon de départ du joueur : entretien offert
            else:
                print(f"⚠️ Impossible de trouver une tuile de départ pour le royaume {kingdom_id}")

    def build_construction(self, tile, construction_name: str, player: int) -> bool:
        """Construit un bâtiment sur la tuile si le joueur a les ressources nécessaires.

        Règles : une route peut coexister avec un bâtiment (Ferme/Mine),
        mais on ne peut pas construire deux routes ni deux bâtiments non-route.
        """
        construction_map = {"Ferme": Farm, "Mine": Mine, "Route": Road, "Scierie": Scierie}
        cls = construction_map.get(construction_name)
        if cls is None:
            return False

        is_road = construction_name == "Route"
        if is_road:
            if any(c.name == "Route" for c in tile.constructions):
                return False
        else:
            if any(c.name != "Route" for c in tile.constructions):
                return False

        resources = self.state.player_resources.get(player, {})
        for res, amount in cls.COST.items():
            if resources.get(res, 0) < amount:
                return False

        for res, amount in cls.COST.items():
            resources[res] -= amount

        tile.constructions.append(cls(tile))
        print(f"Construction '{construction_name}' bâtie sur tuile {tile.id} par joueur {player}")
        return True

    def setup_start_units(self):
        """Fait spawner les unités de départ dans les coins."""
        top_left = self.get_corner_tile("top_left")
        if top_left is not None:
            unit = self.spawn_unit(UnitType.COLON, top_left, owner=0)
            if unit:
                unit.upkeep_cost = 0  # Le colon de départ n'a pas de coût d'entretien
            else:
                print(
                    "⚠️ Impossible de faire spawn le colon de départ dans le coin supérieur gauche"
                )
