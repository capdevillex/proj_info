from typing import List

from world.unit import Unit
from world.biome import Biome


class Tile:
    """
    Représente une unité territoriale (province) cohérente sur la carte.

    Une province regroupe un ensemble de cellules (pixels/coordonnées).
    Elle porte des propriétés physiques et topologiques utilisées pour le gameplay et le rendu.

    Attributes:
        id (int): Identifiant unique de la tuile.
        cells (List[Tuple[int, int]]): Liste des coordonnées (x, y) composant la tuile.
        center (Tuple[float, float]): Point central (centroïde) géométrique de la tuile.
        area (int): Nombre total de cellules (surface).
        neighbors (Set[int]): Ensemble des IDs des tuiles adjacentes.
        biome (Biome): Type de terrain dominant assigné à la tuile.

        units (List[Unit]): NOUVEAU - Liste des unités présentes sur cette tuile
    """

    def __init__(self, id_, cells):
        self.id = id_
        self.cells = cells
        self.center = self._compute_center()
        self.area = len(cells)
        self.neighbors = set()
        self.biome = Biome.BLANK

        # NOUVEAU : initialiser la liste d'unités vide
        self.units: List[Unit] = []

    def _compute_center(self):
        """
        Calcule le centre de masse moyen de la tuile.

        Returns:
            Tuple[float, float]: Coordonnées (x, y) du centre géométrique.
        """
        x = sum(c[0] + 0.5 for c in self.cells) / len(self.cells)
        y = sum(c[1] + 0.5 for c in self.cells) / len(self.cells)
        return (x, y)

    # ========== MÉTHODES POUR GÉRER LES UNITÉS ==========

    def add_unit(self, unit):
        """
        Ajoute une unité à cette tuile.

        Args:
            unit (Unit): L'unité à ajouter

        Exemple :
            tile = game_map.tiles[5]
            unit = Unit(tile_id=5, unit_type=UnitType.SOLDIER)
            tile.add_unit(unit)
        """
        if unit not in self.units:
            self.units.append(unit)
            unit.tile_id = self.id  # S'assurer que l'unité sait sur quelle tuile elle est

    def remove_unit(self, unit):
        """
        Retire une unité de cette tuile.

        Args:
            unit (Unit): L'unité à retirer

        Retour :
            bool : True si l'unité a été trouvée et retirée, False sinon

        Exemple :
            if tile.remove_unit(unit):
                print("Unité retirée")
        """
        if unit in self.units:
            self.units.remove(unit)
            return True
        return False

    def remove_unit_by_id(self, unit_id):
        """
        Retire une unité par son ID.

        Args:
            unit_id (int): L'ID de l'unité à retirer

        Retour :
            Unit : L'unité retirée, ou None si non trouvée

        Exemple :
            removed = tile.remove_unit_by_id(5)
            if removed:
                print(f"Unité {removed.id} retirée")
        """
        for unit in self.units[:]:  # Copie pour éviter les problèmes lors de la modification
            if unit.id == unit_id:
                self.units.remove(unit)
                return unit
        return None

    def get_units(self):
        """
        Retourne la liste des unités sur cette tuile.

        Retour :
            List[Unit] : Liste des unités

        Exemple :
            units = tile.get_units()
            for unit in units:
                print(unit)
        """
        return self.units.copy()  # Retourner une copie pour éviter les modifications externes

    def get_unit_by_id(self, unit_id):
        """
        Trouve une unité par son ID sur cette tuile.

        Args:
            unit_id (int): L'ID de l'unité à chercher

        Retour :
            Unit : L'unité trouvée, ou None si non trouvée

        Exemple :
            unit = tile.get_unit_by_id(5)
            if unit:
                print(f"Trouvée : {unit}")
        """
        for unit in self.units:
            if unit.id == unit_id:
                return unit
        return None

    def has_units(self):
        """
        Vérifie si la tuile a des unités.

        Retour :
            bool : True si au moins une unité est présente

        Exemple :
            if tile.has_units():
                print(f"Cette tuile a {len(tile.units)} unité(s)")
        """

        return len(self.units) > 0

    def get_units_by_owner(self, owner):
        # utile si mind bender/priest
        """
        Récupère toutes les unités d'un propriétaire sur cette tuile.

        Args:
            owner (int): L'ID du propriétaire

        Retour :
            List[Unit] : Les unités du propriétaire

        Exemple :
            units_joueur_0 = tile.get_units_by_owner(0)
        """
        return [unit for unit in self.units if unit.owner == owner]

    def clear_units(self):
        """
        Retire toutes les unités de cette tuile.

        """
        removed = self.units.copy()
        self.units.clear()
        return removed

    def __repr__(self):
        """Représentation textuelle de la tuile"""
        units_str = f", {len(self.units)} unit(s)" if self.units else ""
        return f"Tile(id={self.id}, biome={self.biome.name}, area={self.area}{units_str})"
