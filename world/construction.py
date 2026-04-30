from world.tile import Tile


class Construction:
    def __init__(self, name, cost, tile: Tile):
        self.name = name
        self.cost = cost  # dict of resource type to amount
        self.tile: Tile = tile
        self.boost = {}  # dict of resource type to boost amount

    def __repr__(self):
        return f"Construction(name={self.name}, cost={self.cost}, tile_id={self.tile.id})"


class Farm(Construction):
    COST = {"wood": 5}

    def __init__(self, tile: Tile):
        super().__init__("Ferme", Farm.COST, tile)
        self._calculate_boost()

    def _calculate_boost(self):
        """Calcule le boost de production de la ferme en fonction des ressources de la tuile."""
        resource = self.tile.resource
        if resource and resource.name.startswith("FOOD"):
            level = int(resource.name[-1])
            self.boost["food"] = level
        else:
            self.boost["food"] = 1  # boost de base si pas de ressource alimentaire spécifique


class Mine(Construction):
    COST = {"stone": 2, "wood": 3}

    def __init__(self, tile: Tile):
        super().__init__("Mine", Mine.COST, tile)
        self._calculate_boost()

    def _calculate_boost(self):
        """Calcule le boost de production de la mine en fonction des ressources de la tuile."""
        resource = self.tile.resource
        if resource and resource.name.startswith("IRON"):
            level = int(resource.name[-1])
            self.boost["iron"] = level
            self.boost["stone"] = 1
        elif resource and resource.name.startswith("GOLD"):
            level = int(resource.name[-1])
            self.boost["gold"] = level
            self.boost["stone"] = 1
        elif resource and resource.name.startswith("STONE"):
            level = int(resource.name[-1])
            self.boost["stone"] = level
        else:
            self.boost["iron"] = 1  # boost de base si pas de ressource minière spécifique
            self.boost["stone"] = 1  # boost de base si pas de ressource minière spécifique
            self.boost["gold"] = 0


class Scierie(Construction):
    COST = {"wood": 5}

    def __init__(self, tile: Tile):
        super().__init__("Scierie", Scierie.COST, tile)
        self._calculate_boost()

    def _calculate_boost(self):
        """Calcule le boost de production de la ferme en fonction des ressources de la tuile."""
        resource = self.tile.resource
        if resource and resource.name.startswith("WOOD"):
            level = int(resource.name[-1])
            self.boost["wood"] = level
        else:
            self.boost["wood"] = 1  # boost de base si sur une tuile de forêt sans WOOD


class Road(Construction):
    COST = {"stone": 1, "wood": 1}

    def __init__(self, tile: Tile):
        super().__init__("Route", Road.COST, tile)
        self.boost["movement"] = (
            1  # boost de mouvement pour les unités se déplaçant sur cette tuile
        )
