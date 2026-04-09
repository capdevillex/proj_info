"""
La carte est générée sur une grille 2D où chaque cellule appartient à une province (Tile) et possède
 un biome spécifique. La structure repose sur un diagramme de Voronoi optimisé par relaxation.

1. Placement et relaxation des capitales (points d'origine)
- Des points (capitales ) sont placés aléatoirement grace à l'algo du Poisson-disk-sampling.
- Relaxation de Lloyd : les capitales sont déplacés vers le centre de masse de leur zone d'influence
  pour obtenir une répartition plus organique et équilibrée des futures provinces.

2. Génération des biomes
- Utilisation du bruit de Perlin pour assigner un biome (water, plain, forest, mountain, etc.) à chaque cellule.
- Les biomes sont spatialement continus et servent de contrainte absolue pour les provinces.

3. Assignation des cellules (Voronoi par biome)
- Chaque cellule de la grille est rattachée à la capitale la plus proche, on définira le biome de cette province comme le biome majoriataire
- Cela garantit qu'une province ne chevauche jamais deux biomes différents.

4. Nettoyage et lissage
- Lissage (Smooth) : Réduction du bruit sur les frontières.
- Contraintes de taille : Fusion des provinces trop petites avec leurs voisines et division
  des provinces trop grandes pour maintenir une densité de jeu homogène.
- Stabilisation des centres : On s'assure que le centre géométrique d'une province
  lui appartient toujours pour éviter les formes aberrantes (en forme de "U" ou morcelées).

5. Finalisation des Provinces (Tiles)
- Chaque province est instanciée avec :
    - Son centre (moyenne des positions des cellules).
    - Son biome dominant (on redéfini le biome de toutes les cellule de la province par celui majoritaire).
    - Sa liste de cellules et sa surface.

6. Construction du graphe de voisinage
- Détection de l'adjacence directe entre les cellules pour lier les provinces entre elles.
- Ce graphe permet ensuite de calculer les chemins et les temps de déplacement.

Divers :
 - le temps de déplacement d'une région à une autre est proportionnel à la distance de leur centre
   et pondéré par un coefficient de pénalité de déplacement en fonction du biome
 - les régions sont créées en regroupant les points de même type => Perlin-noise assez "lisse"
"""

import random, math
from typing import List, Tuple, Optional, Dict
from collections import defaultdict, Counter, deque

from utils.noise import perlin_noise


class Tile:
    def __init__(self, id_, cells):
        self.id = id_
        self.cells = cells
        self.center = self._compute_center()
        self.area = len(cells)
        self.neighbors = set()
        self.biome = None

    def _compute_center(self):
        x = sum(c[0] + 0.5 for c in self.cells) / len(self.cells)
        y = sum(c[1] + 0.5 for c in self.cells) / len(self.cells)
        return (x, y)


class Map:
    def __init__(self, width, height, avg_pts_per_tile=35, log=False):
        self.width = width
        self.height = height
        self.n_points = width * height / avg_pts_per_tile
        self.log = log

        self.grid: List[List[Optional[int]]] = [[None] * width for _ in range(height)]
        self.biomes = [[None] * width for _ in range(height)]

        self.capitals: List[Tuple[float, float]] = []
        self.tiles: Dict[int, Tile] = {}

        self._generate()

    # PIPELINE GLOBAL
    def _generate(self):
        self._log("[1] Génération des points d'attraction (Poisson)")
        self.capitals = self._poisson_disk_sampling(self.n_points)

        self._log("[2] Relaxation de Lloyd")
        self._lloyd_relaxation(iterations=2)

        self._log("[3] Génération des biomes")
        self._generate_biomes()

        self._log("[4] Assignation Voronoï")
        self._assign_cells()

        self._log("[5] Nettoyage & contraintes")
        self._cleanup()

        self._log("[6] Construction des provinces")
        self._build_tiles()

        self._log("[7] Voisinage")
        self._build_neighbors()

    def _log(self, msg):
        if self.log:
            print(msg)

    def _poisson_disk_sampling(self, n_points: int) -> List[Tuple[float, float]]:
        """
        Génère des points espacés de manière homogène (Poisson disk sampling simplifié).

        On place aléatoirement des points dans la carte tout en imposant une distance minimale
        entre eux. Cela évite les clusters et garantit une distribution plus naturelle.

        Ici, on utilise une version naïve (rejet) plutôt que Bridson pour rester simple.
        Cela suffit pour des tailles modestes.

        Le but est d'obtenir des points d'attraction bien répartis qui serviront de centres Voronoï.
        """
        points = []
        min_dist = math.sqrt((self.width * self.height) / n_points) * 0.7

        attempts = 0
        while len(points) < n_points and attempts < n_points * 50:
            x = random.uniform(0, self.width)
            y = random.uniform(0, self.height)

            if all((px - x) ** 2 + (py - y) ** 2 >= min_dist**2 for px, py in points):
                points.append((x, y))

            attempts += 1

        return points

    def _lloyd_relaxation(self, iterations=2):
        """
        Applique une relaxation de Lloyd sur les capitales.

        Chaque point est déplacé vers le centre de masse des cellules qui lui sont
        les plus proches (Voronoï discret sur la grille).

        Cela permet de rendre la distribution plus régulière et organique,
        en évitant les zones trop denses ou trop vides.

        Le processus est répété plusieurs fois pour converger vers un équilibre.
        """
        for _ in range(iterations):
            regions = defaultdict(list)

            for y in range(self.height):
                for x in range(self.width):
                    i = self._nearest_capital((x, y))
                    regions[i].append((x, y))

            new_capitals = []
            for i, cells in regions.items():
                if not cells:
                    continue
                cx = sum(c[0] + 0.5 for c in cells) / len(cells)
                cy = sum(c[1] + 0.5 for c in cells) / len(cells)
                new_capitals.append((cx, cy))

            self.capitals = new_capitals

    def _generate_biomes(self, scale=30, octaves=2):
        """
        Génère les biomes via bruit de Perlin.

        Chaque cellule reçoit une valeur continue transformée en catégorie :
        eau, plaine, forêt, montagne.

        Le Perlin garantit une continuité spatiale naturelle, évitant le bruit
        aléatoire pur.
        """
        seed = random.randint(0, 255)

        for y in range(self.height):
            for x in range(self.width):
                n = perlin_noise(x / scale, y / scale, octaves=octaves, base=seed)

                if n < -0.2:
                    self.biomes[y][x] = "water"
                elif n < 0.1:
                    self.biomes[y][x] = "plain"
                elif n < 0.325:
                    self.biomes[y][x] = "forest"
                else:
                    self.biomes[y][x] = "mountain"

    def _assign_cells(self):
        """
        Assigne chaque cellule au point d'attraction le plus proche (Voronoï discret).

        On calcule la distance euclidienne à chaque point d'attraction et on choisit le plus proche.

        Cette étape garantit que toute la carte est couverte sans trous.
        """
        for y in range(self.height):
            for x in range(self.width):
                self.grid[y][x] = self._nearest_capital((x, y))

    def _nearest_capital(self, pos):
        x, y = pos
        return min(
            range(len(self.capitals)),
            key=lambda i: (self.capitals[i][0] - x) ** 2 + (self.capitals[i][1] - y) ** 2,
        )

    def _cleanup(self):
        """
        Nettoie les artefacts du Voronoï discret.

        - Supprime les petites régions isolées
        - Fusionne les provinces trop petites avec leurs voisines
        - Assure la connexité des provinces

        On utilise un flood fill pour détecter les composantes connexes.
        Les petites composantes sont réassignées à un voisin dominant.

        Cela évite les formes aberrantes et améliore la jouabilité.
        """
        visited = [[False] * self.width for _ in range(self.height)]

        def flood_fill(x, y, id_):
            q = deque([(x, y)])
            comp = []
            visited[y][x] = True

            while q:
                cx, cy = q.popleft()
                comp.append((cx, cy))
                for nx, ny in self._neighbors(cx, cy):
                    if not visited[ny][nx] and self.grid[ny][nx] == id_:
                        visited[ny][nx] = True
                        q.append((nx, ny))
            return comp

        for y in range(self.height):
            for x in range(self.width):
                if not visited[y][x]:
                    id_ = self.grid[y][x]
                    comp = flood_fill(x, y, id_)
                    if len(comp) < 10:
                        self._reassign_component(comp)

    def _reassign_component(self, comp):
        neighbor_ids = Counter()
        for x, y in comp:
            for nx, ny in self._neighbors(x, y):
                neighbor_ids[self.grid[ny][nx]] += 1
        if neighbor_ids:
            new_id = neighbor_ids.most_common(1)[0][0]
            for x, y in comp:
                self.grid[y][x] = new_id

    def _build_tiles(self):
        """
        Construit les objets Tile à partir de la grille.

        Chaque province récupère :
        - ses cellules
        - son centre géométrique
        - son biome majoritaire

        Le biome est ensuite uniformisé sur toute la province.

        Cela finalise les entités de jeu manipulables.
        """
        cells_by_id = defaultdict(list)

        for y in range(self.height):
            for x in range(self.width):
                cells_by_id[self.grid[y][x]].append((x, y))

        for id_, cells in cells_by_id.items():
            tile = Tile(id_, cells)
            biome = Counter(self.biomes[y][x] for x, y in cells).most_common(1)[0][0]
            tile.biome = biome
            for x, y in cells:
                self.biomes[y][x] = biome
            self.tiles[id_] = tile

    def _build_neighbors(self):
        """
        Construit le graphe de voisinage entre provinces.

        Deux provinces sont voisines si au moins une de leurs cellules est adjacente.

        Ce graphe est essentiel pour :
        - pathfinding
        - gameplay stratégique
        - diffusion (culture, ressources, etc.)
        """
        for y in range(self.height):
            for x in range(self.width):
                id_ = self.grid[y][x]

                for nx, ny in self._neighbors(x, y):
                    nid = self.grid[ny][nx]
                    if nid != id_:
                        self.tiles[id_].neighbors.add(nid)

    def _neighbors(self, x, y):
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                yield nx, ny
