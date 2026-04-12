""" "
Module de Génération Procédurale de Monde (Hybrid Voronoi/Poisson 4X Map)

Ce module orchestre la création d'un monde structuré en provinces (Tiles) à partir d'une grille 2D.
Il utilise un pipeline combinant partitionnement spatial, bruit cohérent, optimisation topologique
et post-traitements hydrographiques.

---

### Pipeline de Génération :

1.  **Placement des points d'attraction :**
    * Utilise un échantillonnage de type Poisson-disk (Phase I d'Ebeida et al.) pour distribuer les
        centres de provinces.
    * Garantit une distance minimale $r$ entre les points via une grille d'accélération, assurant
        une distribution homogène sans l'aspect rigide d'une grille régulière.

2.  **Cartographie des Biomes (Bruit de Perlin & Modèle Climatique) :**
    * Génération d'une carte de bruit de Perlin multi-octave influencée par un gradient
        radial négatif (favorisant l'eau aux bordures de la carte).
    * Détermination des biomes (Eau, Plaine, Forêt, Montagne) par seuillage discret.
    * **Modèle de Chaleur :** Un second bruit indépendant définit les zones de Désert
        par superposition sur les biomes de Plaine.

3.  **Partitionnement de Voronoï Discret :**
    * Assignation de chaque cellule $(x, y)$ de la grille à la capitale la plus proche
        via une structure spatiale KD-Tree pour optimiser la recherche.

4.  **Nettoyage Morphologique (BFS & Re-assignation) :**
    * Détection des composantes connexes par BFS pour identifier les fragments isolés
        ou les îles de pixels.
    * Fusion des micro-provinces sous un seuil de surface critique vers les voisins
        dominants pour garantir la jouabilité et l'esthétique des formes.

5.  **Cohérence Hydrographique (Système de Ponts et Corridors) :**
    * **Filtrage :** Suppression des micro-lacs isolés.
    * **Connectivité :** Algorithme de recherche de chemin (BFS sur graphe de tuiles)
        pour relier les masses d'eau significatives proches en convertissant des tuiles
        terrestres (hors montagnes) en détroits.
    * **Élargissement :** Analyse des frontières de pixels pour épaissir les corridors
        d'eau trop fins, évitant les passages maritimes visuellement atrophiés.

6.  **Fusion des Tuiles d'Eau (Super-tuiles) :**
    * Regroupement des petites tuiles d'eau en vastes zones maritimes pour optimiser la jouabilité
        maritime.
    * **Distance Transform :** Calcul de la distance de Manhattan par rapport aux côtes.
    * **Sampling Adaptatif :** Placement de nouveaux points d'attraction maritimes plus
        espacés au large et plus denses près des côtes.
    * **Relaxation de Lloyd avec Répulsion :** Centrage des super-tuiles avec un gradient
        les poussant vers le large pour des formes de mers plus naturelles.

7.  **Instanciation de la Topologie (Graphe d'Adjacence) :**
    * Calcul des propriétés finales des objets `Tile` (Biome majoritaire, Cellules, ID).
    * Construction du graphe de voisinage final (adjacence 4 direction + diagonales) permettant le
        pathfinding et les mécaniques de diffusion.

---

### Propriétés Techniques :
* **Complexité Spatiale :** Optimisée par KD-Tree et grilles d'accélération locales.
* **Déterminisme :** Génération 100% pilotée par une `seed` unique.
* **Connectivité Garantie :** Chaque province est une composante connexe unique de pixels
    grâce aux phases de nettoyage BFS et de propagation simultanée (Priority Queue).
"""

import heapq
import random, math, time
from typing import List, Tuple, Optional, Dict
from collections import defaultdict, Counter, deque

from scipy.spatial import KDTree


from world.tile import Tile
from world.biome import Biome
from utils.noise import perlin_noise

VORONOI_AREA_CORRECTION = 1.556  # facteur de correction empirique

# Taille minimale d'un cluster d'eau (en nombre de tuiles) pour être conservé. Les groupes connexes
# de tuiles d'eau dont la taille est <= à cette valeur seront convertis en biome terrestre.
MIN_WATER_CLUSTER_SIZE = 2

# Taille minimale d'une masse d'eau pour tenter de la relier à une voisine.
WATER_CONNECT_MIN_SIZE = 8

# Distance maximale (en sauts de tuile) entre deux masses d'eau pour les relier.
WATER_BRIDGE_MAX_HOPS = 3


def ratio_area_perimeter(cells: List):
    """
    Calcule le ratio area/perimeter d'un groupe de cellules, utilisé pour favoriser les fusions avec des groupes plus compacts.

    Args:
        cells (List[Tuple[int, int]]): Liste des coordonnées des cellules formant le groupe.
    Returns:
        float: Le ratio area/perimeter (plus élevé pour les formes compactes).
    """
    area = len(cells)
    perimeter = 0
    cell_set = set(cells)
    for x, y in cells:
        for nx, ny in [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]:
            if (nx, ny) not in cell_set:
                perimeter += 1
    return area / (perimeter + 10**-12)


class Map:
    """
    Gestionnaire principal de la génération procédurale du monde.

    Cette classe orchestre un pipeline allant de la distribution de points  stochastiques (Poisson
    Disk Sampling) à la construction d'un graphe de voisinage,  en passant par la génération de
    bruit cohérent (Perlin) pour les biomes.

    Attributes:
        width (int): Largeur de la carte en cellules.
        height (int): Hauteur de la carte en cellules.
        seed (int): Graine de génération garantissant le déterminisme.
        tiles (Dict[int, Tile]): Répertoire des objets Tile générés.
        grid (List[List[Optional[int]]]): Grille 2D stockant l'ID de la tuile pour chaque coordonnée.
        biomes (List[List[Biome]]): Grille 2D des types de terrain.
    """

    def __init__(self, width, height, seed, avg_cells_per_tile=35, log=False):
        self.width = width
        self.height = height
        self.avg_cells_per_tile = avg_cells_per_tile
        _corrected_avg_cells_per_tile = avg_cells_per_tile / VORONOI_AREA_CORRECTION
        self.n_points = int(width * height / _corrected_avg_cells_per_tile)
        self.seed = seed
        random.seed(self.seed)
        self.log = log

        self.grid: List[List[Optional[int]]] = [[None] * width for _ in range(height)]
        self.biomes = [[Biome.BLANK] * width for _ in range(height)]

        self.capitals: List[Tuple[float, float]] = []
        self.kdtree = None
        self.tiles: Dict[int, Tile] = {}

        self._generate()

    def serialize(self):
        """
        Sérialise la carte, la génération est purement déterministe en se basant sur la seed, on peut
        donc se contenter de stocker les paramètres de génération pour recréer la même carte à l'identique.

        Returns:
            Dict: Paramètres nécessaires pour reconstruire la carte via la même seed.
        """
        return {
            "width": self.width,
            "height": self.height,
            "avg_cells_per_tile": self.avg_cells_per_tile,
            "seed": self.seed,
            "log": self.log,
        }

    # PIPELINE GLOBAL
    def _generate(self):
        """ "
        Exécute le pipeline de génération complet (Séquence chronologique).

        Séquence :
            Points Poisson -> Bruit Biomes -> Voronoï -> Nettoyage -> Topologie.
        """
        tic = time.perf_counter()
        self._log("[1] Génération des points d'attraction (Poisson)")
        self.capitals = self._ebeida_poisson_phase1(self.n_points)
        self.kdtree = KDTree(self.capitals)
        self._log(f"    {len(self.capitals)} points d'attraction générés")

        # self._log("[2] Relaxation de Lloyd")
        # self._lloyd_relaxation(iterations=1)
        # En pratique ne change pas la forme des tuiles et en le désactivant on gagne 20-30% de temps de génération

        self._log("[2] Génération des biomes")
        self._generate_biomes()

        self._log("[3] Assignation Voronoï")
        self._assign_cells()

        self._log("[4] Nettoyage & contraintes")
        self._cleanup()

        self._log("[5] Construction des provinces")
        self._build_tiles()
        self._log(f"    {len(self.tiles)} provinces générés")
        self._log(f"    mean area : {sum((t.area for t in self.tiles.values()))/len(self.tiles)}")

        self._log("[6] Post-traitement hydrographique")
        self._fix_water_connectivity()

        self._log("[7] Fusion des tuiles d'eau (super-tuiles)")
        self._merge_water_tiles()

        self._log("[8] Voisinage")
        self._build_neighbors()

        self._log("[9] Validation de l'intégrité de la carte")
        self._validate_integrity()

        self._log(f"[perf] generation time : {time.perf_counter() - tic}s")

    def _log(self, msg):
        """Affiche un message de log si l'option est activée"""
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

        ---

        (Non appelé, gardé juste à des fins de documentation)
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

    def _ebeida_poisson_phase1(self, n_points: int):
        """
        Implémentation de la Phase I de l'algorithme d'Ebeida et al. (2011) (https://dl.acm.org/doi/10.1145/1964921.1964944).

        On utilise une grille d'accélération où chaque cellule peut contenir au plus un point (taille = r / sqrt(2)).

        On parcourt les cellules dans un ordre aléatoire et on tente de placer un point uniformément à l'intérieur.

        La validation se fait uniquement sur un voisinage local (5x5), garantissant une complexité quasi-linéaire.

        Cette méthode remplace efficacement le Poisson disk sampling naïf avec de bien meilleures performances pour un grand nombre de points.
        """

        width, height = self.width, self.height

        # distance cible entre points
        r = math.sqrt((width * height) / n_points) * 0.9

        cell_size = r / math.sqrt(2)

        grid_w = int(width / cell_size) + 1
        grid_h = int(height / cell_size) + 1

        # grille : stocke index du point
        grid = [[-1 for _ in range(grid_w)] for _ in range(grid_h)]

        points = []

        # liste des cellules mélangée (important pour uniformité)
        cells = [(x, y) for y in range(grid_h) for x in range(grid_w)]
        random.shuffle(cells)

        def fits(px, py, gx, gy):
            """Vérifie localement si un point respecte la distance minimale."""
            for ny in range(max(0, gy - 2), min(grid_h, gy + 3)):
                for nx in range(max(0, gx - 2), min(grid_w, gx + 3)):
                    idx = grid[ny][nx]
                    if idx != -1:
                        qx, qy = points[idx]
                        if (qx - px) ** 2 + (qy - py) ** 2 < r * r:
                            return False
            return True

        # Phase I : un seul essai par cellule
        for gx, gy in cells:
            px = (gx + random.random()) * cell_size
            py = (gy + random.random()) * cell_size

            if not (0 <= px < width and 0 <= py < height):
                continue

            if fits(px, py, gx, gy):
                grid[gy][gx] = len(points)
                points.append((px, py))

        if len(points) < width * height / self.avg_cells_per_tile * 0.7:
            raise RuntimeError(
                f"Poisson sampling failed to generate enough points: {len(points)} / {n_points}"
            )
        return points

    def _lloyd_relaxation(self, iterations=2):
        """
        Applique une relaxation de Lloyd sur les capitales.

        Chaque point est déplacé vers le centre de masse des cellules qui lui sont
        les plus proches (Voronoï discret sur la grille).

        Cela permet de rendre la distribution plus régulière et organique, en évitant les zones trop denses ou trop vides.

        Transforme un Voronoï irrégulier en un pavage de Centroïdal Voronoï (CVT) plus esthétique et équilibré.

        ---

        (Non appelé, gardé juste à des fins de documentation)
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

    def _generate_biomes(self, octaves=4):
        """
        Génère les biomes via bruit de Perlin multi-octave.

        Chaque cellule reçoit une valeur continue transformée en catégorie : eau, plaine, forêt,
        montagne ou désert.

        Le désert est déterminé par un second bruit de Perlin indépendant ("heat map") appliqué
        uniquement dans les zones de plaine.

        Args:
            octaves (int): Niveau de détail du bruit (persistance des fréquences).
        """
        scale = self.avg_cells_per_tile * 1.15
        # Échelle plus large pour le bruit de chaleur : les zones désertiques sont plus étendues et moins fragmentées que la topographie de base.
        heat_scale = self.avg_cells_per_tile * 3
        heat_seed = (
            self.seed + 7919
        ) % 255  # Décalage de seed pour que la heat map soit indépendante du bruit de terrain.

        # Seuil au-dessus duquel une cellule de plaine devient désert.
        # ~0.15 donne environ 9% de déserts, ce qui est rare mais visible.
        DESERT_HEAT_THRESHOLD = 0.15

        # stats pour les biomes
        water_ct = 0
        plain_ct = 0
        forest_ct = 0
        mountain_ct = 0
        desert_ct = 0

        for y in range(self.height):
            for x in range(self.width):
                n = perlin_noise(
                    x / scale, y / scale, octaves=octaves, lacunarity=1.75, base=self.seed % 255
                )

                # ajout d'un gradient négatif qui part des bords de la carte et vers le centre
                nx = 1 - (2 * x / self.width - 1 + 10**-5) ** 2
                ny = 1 - (2 * y / self.height - 1 + 10**-5) ** 2
                deniv = min(math.log(2.25 * min(nx, ny)), 0.1)
                n += 0.7 * deniv

                if n < -0.225:
                    self.biomes[y][x] = Biome.WATER
                    water_ct += 1
                elif n < 0.325:
                    heat = perlin_noise(
                        x / heat_scale, y / heat_scale, octaves=2, lacunarity=2.0, base=heat_seed
                    )
                    if n < 0.14:
                        # Zone de plaine : on applique la heat map pour détecter le désert.
                        if heat > DESERT_HEAT_THRESHOLD:
                            self.biomes[y][x] = Biome.DESERT
                            desert_ct += 1
                        else:
                            self.biomes[y][x] = Biome.PLAIN
                            plain_ct += 1
                    else:
                        self.biomes[y][x] = (
                            Biome.FOREST if heat < DESERT_HEAT_THRESHOLD else Biome.PLAIN
                        )
                        forest_ct += 1
                else:
                    self.biomes[y][x] = Biome.MOUNTAIN
                    mountain_ct += 1
        total = self.width * self.height
        self._log(
            f"    Biome distribution: WATER={water_ct/total:.2%}, PLAIN={plain_ct/total:.2%}, DESERT={desert_ct/total:.2%}, FOREST={forest_ct/total:.2%}, MOUNTAIN={mountain_ct/total:.2%}"
        )

    def _assign_cells(self):
        """
        Assigne chaque cellule au point d'attraction le plus proche (Voronoï discret).

        Utilise un KD-Tree pour optimiser la recherche du point d'attraction le plus proche pour chaque cellule (x, y).

        Cette étape garantit que toute la carte est couverte et sans trous.
        """
        coords = [(x, y) for y in range(self.height) for x in range(self.width)]
        _, indices = self.kdtree.query(coords)
        for i, (x, y) in enumerate(coords):
            self.grid[y][x] = int(indices[i])

    def _nearest_capital(self, pos):
        """
        Trouve l'index du point d'attraction le plus proche d'une coordonnée donnée.

        Args:
            pos (Tuple[int, int]): Position cible.
        Returns:
            int: Index (ID) de la capitale la plus proche.

        ---

        (Non appelé, gardé juste à des fins de documentation)
        """
        if self.kdtree is None:
            raise RuntimeError("This should not happen")
        _, index = self.kdtree.query(pos)
        return int(index)

    def _cleanup(self):
        """
        Post-traitement morphologique pour garantir l'intégrité de la carte, nettoie les artefacts du Voronoï discret.

        - Supprime les petites régions isolées
        - Fusionne les provinces trop petites avec leurs voisines
        - Assure la connexité des provinces

        On utilise un BFS pour détecter les composantes connexes.
        Les petites composantes sont réassignées à un voisin dominant.

        Cela évite les formes aberrantes et améliore la jouabilité.
        """
        visited = [[False] * self.width for _ in range(self.height)]

        def bfs(x, y, id_):
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
                    comp = bfs(x, y, id_)
                    if len(comp) < self.avg_cells_per_tile * 0.3:
                        self._reassign_component(comp)

    def _reassign_component(self, comp):
        """
        Réassigne un groupe de cellules isolées au voisin le plus représenté.

        Args:
            comp (List[Tuple[int, int]]): Liste de cellules formant une île isolée.
        """
        # self._log(f"[reassign comp] : {comp}")
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
        Instancie les objets Tile et harmonise les biomes.

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

    def _fix_water_connectivity(self):
        """
        Assure la cohérence hydrographique de la carte en deux passes.

        **Passe 1 — Suppression des micro-points d'eau :**
            Les composantes connexes de tuiles d'eau de taille <= MIN_WATER_CLUSTER_SIZE
            sont converties en biome terrestre. Cela élimine les points d'eau ponctuels
            (1-2 provinces) incohérents.

        **Passe 2 — Connexion des masses d'eau proches :**
            Pour chaque paire de masses d'eau significatives (>= WATER_CONNECT_MIN_SIZE),
            on cherche un chemin de tuiles intermédiaires de longueur <= WATER_BRIDGE_MAX_HOPS
            qui ne traverse pas de montagne. Si un tel chemin existe, les tuiles terrestres
            sur le chemin le plus court sont converties en eau, créant un détroit naturel.

        Note : cette méthode doit être appelée après `_build_tiles` et avant `_build_neighbors`.
        """

        # tile.neighbors est vide à ce stade, on construit le graphe complet à la volée.
        tile_adjacency: Dict[int, set] = defaultdict(set)
        for y in range(self.height):
            for x in range(self.width):
                tid = self.grid[y][x]
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height:
                        nid = self.grid[ny][nx]
                        if nid != tid and nid is not None and tid is not None:
                            tile_adjacency[tid].add(nid)

        water_tile_ids = {tid for tid, t in self.tiles.items() if t.biome == Biome.WATER}

        if not water_tile_ids:
            return

        # --- BFS pour identifier les composantes connexes d'eau ---
        def water_components(wids):
            visited: set = set()
            comps: List[List[int]] = []
            for start in wids:
                if start in visited:
                    continue
                comp = []
                q = deque([start])
                visited.add(start)
                while q:
                    cur = q.popleft()
                    comp.append(cur)
                    for nb in tile_adjacency[cur]:
                        if nb not in visited and nb in wids:
                            visited.add(nb)
                            q.append(nb)
                comps.append(comp)
            return comps

        components = water_components(water_tile_ids)

        # Passe 1 : supprimer les micro-clusters d'eau
        small_ids: set = set()
        large_components: List[List[int]] = []
        for comp in components:
            if len(comp) <= MIN_WATER_CLUSTER_SIZE:
                small_ids.update(comp)
                # self._log(f"[water] micro-cluster supprimé ({len(comp)} tuile(s))")
            else:
                large_components.append(comp)

        for tid in small_ids:
            self._convert_water_tile_to_land(tid, tile_adjacency)

        # Passe 2 : relier les masses d'eau significatives proches
        # On ne tente de relier que les composantes >= WATER_CONNECT_MIN_SIZE.
        significant = [c for c in large_components if len(c) >= WATER_CONNECT_MIN_SIZE]

        if len(significant) < 2:
            self._log(
                f"[water] {len(significant)} masse(s) d'eau significative(s), pas de connexion à établir."
            )
            return

        # Pour chaque paire de composantes significatives distinctes, on cherche
        # le chemin le plus court entre leurs tuiles via un BFS sur le graphe de tuiles.
        # On bloque les tuiles de montagne pour ne pas percer les reliefs.
        # Si le chemin (hors les tuiles d'eau de départ/arrivée) a <= WATER_BRIDGE_MAX_HOPS
        # tuiles terrestres, on les convertit en eau.
        comp_sets = [set(c) for c in significant]
        bridges_built = 0

        for i in range(len(significant)):
            for j in range(i + 1, len(significant)):
                set_i, set_j = comp_sets[i], comp_sets[j]

                # BFS depuis toutes les tuiles de la composante i vers la composante j.
                # On s'arrête dès qu'on atteint une tuile de j ou qu'on dépasse la distance max.
                # `prev` stocke le prédécesseur pour reconstruire le chemin.
                prev: Dict[int, Optional[int]] = {tid: None for tid in set_i}
                frontier = deque(set_i)
                found: Optional[int] = None
                land_hops: Dict[int, int] = {tid: 0 for tid in set_i}  # nb de sauts terrestres

                while frontier and found is None:
                    cur = frontier.popleft()
                    cur_hops = land_hops[cur]
                    if cur_hops > WATER_BRIDGE_MAX_HOPS:
                        continue
                    for nb in tile_adjacency[cur]:
                        if nb in prev:
                            continue
                        nb_biome = self.tiles[nb].biome
                        # Bloquer les montagnes
                        if nb_biome == Biome.MOUNTAIN:
                            continue
                        prev[nb] = cur
                        if nb in set_j:
                            found = nb
                            break
                        # Compter les sauts terrestres (hors eau)
                        nb_hops = cur_hops if nb_biome == Biome.WATER else cur_hops + 1
                        land_hops[nb] = nb_hops
                        frontier.append(nb)

                if found is None:
                    continue  # pas de chemin court trouvé, on laisse les masses séparées

                # Reconstruction du chemin et conversion des tuiles terrestres en eau.
                path = []
                cur = found
                while cur is not None:
                    path.append(cur)
                    cur = prev[cur]
                path.reverse()

                converted = 0
                for tid in path:
                    if self.tiles[tid].biome != Biome.WATER:
                        self._convert_land_tile_to_water(tid)
                        water_tile_ids.add(tid)
                        set_i.add(tid)
                        set_j.add(tid)
                        converted += 1

                if converted > 0:
                    bridges_built += 1
                    # self._log(
                    #     f"[water] pont créé entre comp {i} et comp {j} ({converted} tuile(s) converties)"
                    # )

                # Fusionner les deux composantes dans comp_sets pour les prochaines paires.
                comp_sets[i] = set_i | set_j
                comp_sets[j] = comp_sets[i]

        self._log(f"[water] {bridges_built} pont(s) hydrographique(s) établi(s).")

        # Passe 3 : élargissement des corridors trop fins
        self._widen_water_corridors(water_tile_ids, tile_adjacency)

    def _widen_water_corridors(self, water_tile_ids: set, tile_adjacency: Dict[int, set]):
        """
        Épaissit les corridors d'eau trop fins après la création des ponts.

        Algorithme :
          1. On constitue l'ensemble des tuiles d'eau qui ont strictement moins de 4 voisines
             eau (au sens de tile_adjacency). Ce sont les tuiles "en bordure étroite".
          2. Pour chaque tuile T de cet ensemble, on itère sur ses voisines eau W.
             On compte les pixels de frontière 4-connexe entre T et W.
             Si ce contact est < 4 (la connexion entre T et W est trop fine) :
               - On prend l'intersection des voisines de T et de W (hors eau, hors montagne).
               - Parmi ces candidates, on convertit en eau celle dont la somme de pixels de
                 frontière avec T et W est maximale.
          3. Les tuiles nouvellement converties sont ajoutées à water_tile_ids et
             tile_adjacency pour que les passes suivantes les voient.

        Args:
            water_tile_ids: Ensemble des IDs de tuiles d'eau (modifié en place).
            tile_adjacency: Graphe d'adjacence inter-tuiles complet (modifié en place).
        """
        # Calcul du cache des frontières pixel entre tuiles voisines.
        # On ne calcule que les paires (a, b) avec a < b pour éviter les doublons.
        border_cache: Dict[tuple, int] = {}

        def pixel_border(a: int, b: int) -> int:
            key = (min(a, b), max(a, b))
            if key not in border_cache:
                cells_b = set(self.tiles[b].cells)
                count = 0
                for x, y in self.tiles[a].cells:
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        if (x + dx, y + dy) in cells_b:
                            count += 1
                border_cache[key] = count
            return border_cache[key]

        # On itère jusqu'à convergence : une conversion peut créer de nouvelles paires trop fines.
        # En pratique 2-3 passes suffisent largement.
        MAX_PASSES = 3
        for pass_num in range(MAX_PASSES):
            widened = 0

            # Étape 1 : tuiles d'eau avec < 5 voisines eau.
            thin_water = {
                tid
                for tid in water_tile_ids
                if sum(1 for nb in tile_adjacency[tid] if nb in water_tile_ids) < 4
            }

            for tid in thin_water:
                water_neighbors = [nb for nb in tile_adjacency[tid] if nb in water_tile_ids]

                for w_nb in water_neighbors:
                    if pixel_border(tid, w_nb) >= 5:
                        continue  # connexion déjà suffisamment large

                    # Intersection des voisines terrestres non-montagne de tid et w_nb.
                    candidates = (tile_adjacency[tid] - water_tile_ids) & (
                        tile_adjacency[w_nb] - water_tile_ids
                    )
                    candidates = {c for c in candidates if self.tiles[c].biome != Biome.MOUNTAIN}

                    if not candidates:
                        continue

                    # On choisit le candidat qui maximise la frontière totale avec tid + w_nb.
                    best = max(
                        candidates, key=lambda c: pixel_border(c, tid) + pixel_border(c, w_nb)
                    )

                    self._convert_land_tile_to_water(best)
                    water_tile_ids.add(best)

                    # Mise à jour de tile_adjacency pour les passes suivantes.
                    for nb in tile_adjacency[best]:
                        tile_adjacency[nb].add(best)

                    # Invalider le cache pour les paires impliquant best.
                    keys_to_drop = [k for k in border_cache if best in k]
                    for k in keys_to_drop:
                        del border_cache[k]

                    widened += 1
                    # self._log(f"[water] élargissement : tuile {best} convertie en eau")

            self._log(
                f"[water] passe d'élargissement {pass_num + 1} : {widened} tuile(s) ajoutée(s)"
            )
            if widened == 0:
                break

    def _convert_water_tile_to_land(self, tile_id: int, tile_adjacency: Dict[int, set]):
        """
        Convertit une tuile d'eau en biome terrestre (PLAIN ou DESERT).

        Le biome est choisi selon le voisinage dominant (hors eau) dans tile_adjacency.

        Args:
            tile_id (int): Identifiant de la tuile à convertir.
            tile_adjacency (Dict[int, set]): Graphe d'adjacence inter-tuiles pré-calculé.
        """
        tile = self.tiles[tile_id]

        land_neighbor_biomes = [
            self.tiles[nid].biome
            for nid in tile_adjacency.get(tile_id, set())
            if nid in self.tiles and self.tiles[nid].biome != Biome.WATER
        ]

        if land_neighbor_biomes:
            dominant = Counter(land_neighbor_biomes).most_common(1)[0][0]
            new_biome = dominant if dominant in (Biome.DESERT, Biome.PLAIN) else Biome.PLAIN
        else:
            new_biome = Biome.PLAIN

        tile.biome = new_biome
        for x, y in tile.cells:
            self.biomes[y][x] = new_biome

        # self._log(f"[water->land] tuile {tile_id} convertie en {new_biome.name}")

    def _convert_land_tile_to_water(self, tile_id: int, biome=Biome.WATER):
        """
        Convertit une tuile terrestre en eau pour créer un détroit entre deux masses d'eau.

        Args:
            tile_id (int): Identifiant de la tuile à convertir.
        """
        tile = self.tiles[tile_id]
        tile.biome = biome
        for x, y in tile.cells:
            self.biomes[y][x] = biome

        # self._log(f"[land->water] tuile {tile_id} convertie en eau (détroit)")

    def _rebuild_tiles_from_grid(self):
        self.tiles.clear()

        cells_by_id = defaultdict(list)

        for y in range(self.height):
            for x in range(self.width):
                tid = self.grid[y][x]
                if tid is not None:
                    cells_by_id[tid].append((x, y))

        for tid, cells in cells_by_id.items():
            tile = Tile(tid, cells)
            biome = Counter(self.biomes[y][x] for x, y in cells).most_common(1)[0][0]
            tile.biome = biome
            self.tiles[tid] = tile

    def _merge_water_tiles(self, target_size: int = 12):
        """
        Fusionne les tuiles d'eau proches en super-tuiles plus grandes pour améliorer la jouabilité.

        Pipeline :
            A. Distance Transform : Calcul de la distance à la côte pour chaque cellule d'eau
            B. Poisson Disk Sampling adaptatif : Placement des points d'attraction avec densité variable
            C. Relaxation de Lloyd : Amélioration de la régularité avec répulsion côtière
            D. Assignation Voronoï : Propagation par flood fill simultané
            E. Nettoyage et réassignation : Traitement des tuiles problématiques
            F. Reconstruction : Création des nouvelles tuiles
        """
        self._log("[Fusion] Début de la fusion des tuiles d'eau")

        # Collecte initiale
        water_cells_set, land_cells, land_tiles = self._collect_water_and_land_cells()

        if not water_cells_set:
            self._log("[Fusion] Aucune cellule d'eau à fusionner")
            return

        # Pipeline de fusion
        self._log("[Fusion A] Distance Transform")
        distance_map = self._compute_distance_transform(water_cells_set, land_cells)

        self._log("[Fusion B] Poisson Disk Sampling adaptatif")
        seeds = self._adaptive_poisson_sampling(water_cells_set, distance_map, target_size)
        self._log(f"[Fusion B] {len(seeds)} points d'attraction générés")

        self._log("[Fusion C] Relaxation de Lloyd avec répulsion côtière")
        seeds = self._lloyd_relaxation_with_repulsion(seeds, water_cells_set, distance_map)

        self._log("[Fusion D] Assignation Voronoï par flood fill")
        grid_assignment = self._voronoi_flood_fill(seeds, water_cells_set)

        self._log("[Fusion E] Nettoyage et réassignation des tuiles problématiques")
        water_groups = self._cleanup_and_reassign_problematic_tiles(
            grid_assignment, seeds, water_cells_set, target_size
        )

        self._log("[Fusion F] Reconstruction des tuiles")
        self._reconstruct_tiles(water_groups, land_tiles)
        self._rebuild_tiles_from_grid()

        self._log(f"[Fusion] Terminé - {len(self.tiles)} tuiles au total")

    # Méthodes dédiées au partitionnement des tuiles d'eau

    def _collect_water_and_land_cells(self):
        """
        Collecte les cellules d'eau et de terre.

        Returns:
            Tuple[set, set, list]: (water_cells_set, land_cells, land_tiles)
        """
        water_cells_set = set()
        land_cells = set()
        land_tiles = []

        for tid, tile in self.tiles.items():
            if tile.biome == Biome.WATER:
                water_cells_set.update(tile.cells)
            else:
                land_tiles.append(tile)
                land_cells.update(tile.cells)

        return water_cells_set, land_cells, land_tiles

    def _compute_distance_transform(self, water_cells_set, land_cells):
        """
        Calcule la distance de chaque cellule d'eau à la terre la plus proche (Manhattan).

        Args:
            water_cells_set: Ensemble des cellules d'eau
            land_cells: Ensemble des cellules de terre

        Returns:
            Dict: Mapping (x, y) -> distance
        """
        distance_map = {pos: float("inf") for pos in water_cells_set}
        dist_queue = deque()

        # Initialisation avec les cellules d'eau adjacentes à la terre
        for cx, cy in water_cells_set:
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                if (cx + dx, cy + dy) in land_cells:
                    distance_map[(cx, cy)] = 1
                    dist_queue.append((cx, cy))
                    break

        # Propagation BFS
        while dist_queue:
            curr = dist_queue.popleft()
            d = distance_map[curr]
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (curr[0] + dx, curr[1] + dy)
                if neighbor in distance_map and distance_map[neighbor] == float("inf"):
                    distance_map[neighbor] = d + 1
                    dist_queue.append(neighbor)

        return distance_map

    def _adaptive_poisson_sampling(self, water_cells_set, distance_map, target_size):
        """
        Poisson Disk Sampling adaptatif avec densité variable selon la distance à la côte.

        Args:
            water_cells_set: Ensemble des cellules d'eau
            distance_map: Mapping (x, y) -> distance à la côte
            target_size: Taille cible des tuiles

        Returns:
            List[Tuple[float, float]]: Liste des points d'attraction (seeds)
        """
        # Rayon de base pour la densité cible
        r_base = math.sqrt(
            len(water_cells_set)
            / (max(1, len(water_cells_set) / (self.avg_cells_per_tile * target_size * 1.2)))
        )

        # Paramètres de densité : 1.5x plus dense à la côte
        r_min = r_base  # Près des côtes
        r_max = r_base * 1.75  # Large

        seeds = []
        # Grille d'accélération basée sur r_max
        cell_size = r_max / 1.414
        grid_w, grid_h = int(self.width / cell_size) + 1, int(self.height / cell_size) + 1
        accel_grid = [[-1 for _ in range(grid_w)] for _ in range(grid_h)]

        def get_local_r(pos):
            d = distance_map.get(pos, 0)
            # Interpolation douce du rayon : sature à self.avg_cells_per_tile pixels de la côte
            t = min(d / self.avg_cells_per_tile, 1.0)
            return r_min + (r_max - r_min) * t

        water_candidates = list(water_cells_set)
        random.shuffle(water_candidates)

        for cx, cy in water_candidates:
            px, py = cx + 0.5, cy + 0.5
            local_r = get_local_r((cx, cy))

            # Vérification du voisinage
            gx, gy = int(px / cell_size), int(py / cell_size)
            too_close = False
            for ny in range(max(0, gy - 2), min(grid_h, gy + 3)):
                for nx in range(max(0, gx - 2), min(grid_w, gx + 3)):
                    idx = accel_grid[ny][nx]
                    if idx != -1:
                        sx, sy = seeds[idx]
                        dist_sq = (sx - px) ** 2 + (sy - py) ** 2
                        combined_r = max(local_r, get_local_r((int(sx), int(sy))))
                        if dist_sq < combined_r**2:
                            too_close = True
                            break
                if too_close:
                    break

            if not too_close:
                accel_grid[gy][gx] = len(seeds)
                seeds.append((px, py))

        return seeds

    def _lloyd_relaxation_with_repulsion(self, seeds, water_cells_set, distance_map, iterations=3):
        """
        Relaxation de Lloyd avec répulsion côtière.

        Args:
            seeds: Liste des points d'attraction
            water_cells_set: Ensemble des cellules d'eau
            distance_map: Mapping (x, y) -> distance à la côte
            iterations: Nombre d'itérations

        Returns:
            List[Tuple[float, float]]: Seeds relaxés
        """
        for iteration in range(iterations):
            groups = defaultdict(list)

            # BFS temporaire pour assigner les cellules aux seeds actuelles
            temp_assignment = {
                (int(s[0]), int(s[1])): i
                for i, s in enumerate(seeds)
                if (int(s[0]), int(s[1])) in water_cells_set
            }
            q = deque(temp_assignment.keys())

            while q:
                curr = q.popleft()
                idx = temp_assignment[curr]
                groups[idx].append(curr)
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nb = (curr[0] + dx, curr[1] + dy)
                    if nb in water_cells_set and nb not in temp_assignment:
                        temp_assignment[nb] = idx
                        q.append(nb)

            new_seeds = []
            for i, old_seed in enumerate(seeds):
                cells = groups[i]
                if not cells:
                    new_seeds.append(old_seed)
                    continue

                # Centroïde
                tx = sum(c[0] for c in cells) / len(cells)
                ty = sum(c[1] for c in cells) / len(cells)

                # Répulsion : on pousse vers le gradient positif de distance
                d_center = distance_map.get((int(tx), int(ty)), 20)
                if d_center < 15:
                    push_x, push_y = 0, 0
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        if distance_map.get((int(tx) + dx, int(ty) + dy), 0) > d_center:
                            push_x += dx
                            push_y += dy

                    factor = (15 - d_center) / 15 * 1.5
                    tx += push_x * factor
                    ty += push_y * factor

                # Validation : rester dans l'eau
                if (int(tx), int(ty)) in water_cells_set:
                    new_seeds.append((tx, ty))
                else:
                    new_seeds.append(old_seed)

            seeds = new_seeds

        return seeds

    def _voronoi_flood_fill(self, seeds, water_cells_set):
        """
        Assignation Voronoï par propagation simultanée (flood fill avec priority queue).

        Args:
            seeds: Liste des points d'attraction
            water_cells_set: Ensemble des cellules d'eau

        Returns:
            Dict: Mapping (x, y) -> seed_index
        """
        grid_assignment = {}
        priority_queue = []

        for i, seed in enumerate(seeds):
            pos = (int(seed[0]), int(seed[1]))
            if pos in water_cells_set:
                grid_assignment[pos] = i
                heapq.heappush(priority_queue, (0, pos[0], pos[1], i, pos[0], pos[1]))

        while priority_queue:
            _, x, y, s_idx, sx, sy = heapq.heappop(priority_queue)

            curr = (x, y)
            if grid_assignment.get(curr) != s_idx and curr in grid_assignment:
                continue

            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (x + dx, y + dy)
                if neighbor in water_cells_set and neighbor not in grid_assignment:
                    new_cost = (neighbor[0] - sx) ** 2 + (neighbor[1] - sy) ** 2
                    grid_assignment[neighbor] = s_idx
                    heapq.heappush(
                        priority_queue, (new_cost, neighbor[0], neighbor[1], s_idx, sx, sy)
                    )

        return grid_assignment

    def _cleanup_and_reassign_problematic_tiles(
        self, grid_assignment, seeds, water_cells_set, target_size
    ):
        """
        Nettoyage et réassignation des tuiles problématiques (trop petites).

        Nouvelle approche :
        - Identifier les tuiles problématiques
        - Supprimer ces tuiles et leurs voisines directes
        - Collecter toutes les cellules à réassigner
        - Pour chaque composante connexe, faire une assignation BFS avec n_comp - 1 points
          (n_comp = nombre de tuiles supprimées dans cette composante)

        Args:
            grid_assignment: Mapping (x, y) -> seed_index
            seeds: Liste des points d'attraction
            water_cells_set: Ensemble des cellules d'eau
            target_size: Taille cible des tuiles

        Returns:
            Dict: Mapping seed_index -> list of cells
        """
        # Grouper les cellules par seed
        water_groups = defaultdict(list)
        for pos, s_idx in grid_assignment.items():
            water_groups[s_idx].append(pos)

        min_area = (self.avg_cells_per_tile * target_size) * 0.4

        # Identifier les tuiles problématiques (trop petites)
        problematic_indices = set()
        for s_idx, cells in water_groups.items():
            if 0 < len(cells) < min_area:
                problematic_indices.add(s_idx)

        if not problematic_indices:
            self._log("[Fusion E] Aucune tuile problématique détectée")
            return water_groups

        self._log(f"[Fusion E] {len(problematic_indices)} tuiles problématiques détectées")

        # Construire le graphe d'adjacence entre tuiles
        tile_neighbors = defaultdict(set)
        for pos, s_idx in grid_assignment.items():
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor_pos = (pos[0] + dx, pos[1] + dy)
                if neighbor_pos in grid_assignment:
                    neighbor_idx = grid_assignment[neighbor_pos]
                    if neighbor_idx != s_idx:
                        tile_neighbors[s_idx].add(neighbor_idx)

        # Collecter les tuiles à supprimer (problématiques + leurs voisines)
        tiles_to_remove = set(problematic_indices)
        for prob_idx in problematic_indices:
            tiles_to_remove.update(tile_neighbors[prob_idx])
            for neighbor in tile_neighbors[prob_idx]:
                tiles_to_remove.update(tile_neighbors[neighbor])

        self._log(f"[Fusion E] {len(tiles_to_remove)} tuiles à supprimer (incluant voisines)")

        # Collecter toutes les cellules à réassigner
        cells_to_reassign = set()
        for s_idx in tiles_to_remove:
            cells_to_reassign.update(water_groups[s_idx])
            del water_groups[s_idx]

        if not cells_to_reassign:
            return water_groups

        # Identifier les composantes connexes dans les cellules à réassigner
        components = self._find_connected_components(cells_to_reassign)
        num_components = len(components)

        self._log(
            f"[Fusion E] {len(cells_to_reassign)} cellules à réassigner en {num_components} composante(s)"
        )

        # Traiter chaque composante connexe séparément
        next_seed_idx = max(water_groups.keys()) + 1 if water_groups else 0

        for comp_idx, component in enumerate(components):
            # Calculer combien de tuiles ont été supprimées dans cette composante
            # (approximation basée sur la taille de la composante)
            comp_size = len(component)

            # Nombre de seeds pour cette composante : au moins 1, sinon basé sur la taille
            num_seeds_for_comp = max(1, comp_size // (self.avg_cells_per_tile * target_size))

            self._log(
                f"[Fusion E] Composante {comp_idx + 1}/{num_components} : "
                f"{comp_size} cellules, {num_seeds_for_comp} seed(s)"
            )

            # Générer des seeds pour cette composante
            comp_seeds = self._generate_seeds_for_cells(component, num_seeds_for_comp)

            # Assigner les cellules de cette composante avec BFS (garantit la connexité)
            comp_assignment = self._assign_cells_to_seeds_bfs(component, comp_seeds)

            # Intégrer les nouvelles assignations
            for local_idx, cells in comp_assignment.items():
                if cells:  # Ne pas créer de groupes vides
                    water_groups[next_seed_idx] = cells
                    next_seed_idx += 1

        self._log(f"[Fusion E] Réassignation terminée - {len(water_groups)} groupes d'eau")

        return water_groups

    def _find_connected_components(self, cells_set):
        """
        Trouve les composantes connexes dans un ensemble de cellules.

        Args:
            cells_set: Ensemble de cellules (x, y)

        Returns:
            List[set]: Liste des composantes connexes
        """
        visited = set()
        components = []

        for start_cell in cells_set:
            if start_cell in visited:
                continue

            # BFS pour trouver la composante
            component = set()
            queue = deque([start_cell])
            visited.add(start_cell)

            while queue:
                cell = queue.popleft()
                component.add(cell)

                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    neighbor = (cell[0] + dx, cell[1] + dy)
                    if neighbor in cells_set and neighbor not in visited:
                        visited.add(neighbor)
                        queue.append(neighbor)

            components.append(component)

        return components

    def _generate_seeds_for_cells(self, cells_set, num_seeds):
        """
        Génère des points d'attraction pour un ensemble de cellules.

        Args:
            cells_set: Ensemble de cellules
            num_seeds: Nombre de seeds à générer

        Returns:
            List[Tuple[float, float]]: Liste des seeds
        """
        if num_seeds <= 0:
            return []

        cells_list = list(cells_set)

        if num_seeds >= len(cells_list):
            # Un seed par cellule
            return [(x + 0.5, y + 0.5) for x, y in cells_list]

        # Échantillonnage aléatoire simple
        sampled = random.sample(cells_list, num_seeds)
        return [(x + 0.5, y + 0.5) for x, y in sampled]

    def _assign_cells_to_seeds(self, cells_set, seeds):
        """
        Assigne des cellules aux seeds les plus proches (méthode simple, sans garantie de connexité).

        ATTENTION : Cette méthode peut créer des tuiles non-connexes si des bras de terre
        traversent la zone. Utilisez _assign_cells_to_seeds_bfs pour garantir la connexité.

        Args:
            cells_set: Ensemble de cellules à assigner
            seeds: Liste des seeds

        Returns:
            Dict: Mapping seed_index -> list of cells
        """
        if not seeds:
            return {}

        assignment = defaultdict(list)

        for cell in cells_set:
            # Trouver le seed le plus proche
            min_dist = float("inf")
            closest_idx = 0

            for i, seed in enumerate(seeds):
                dist_sq = (cell[0] - seed[0]) ** 2 + (cell[1] - seed[1]) ** 2
                if dist_sq < min_dist:
                    min_dist = dist_sq
                    closest_idx = i

            assignment[closest_idx].append(cell)

        return assignment

    def _assign_cells_to_seeds_bfs(self, cells_set, seeds):
        """
        Assigne des cellules aux seeds en utilisant un BFS simultané.

        Cette méthode garantit que chaque tuile créée est connexe (pas de bras de terre
        qui la traverse). Le BFS propage depuis chaque seed simultanément, en respectant
        la connexité 4-adjacente.

        Args:
            cells_set: Ensemble de cellules à assigner (doit être connexe)
            seeds: Liste des seeds

        Returns:
            Dict: Mapping seed_index -> list of cells (chaque groupe est garanti connexe)
        """
        if not seeds:
            return {}

        if len(seeds) == 1:
            # Un seul seed : toutes les cellules lui appartiennent
            return {0: list(cells_set)}

        # Initialisation : chaque seed démarre sur la cellule la plus proche
        assignment = {}
        priority_queue = []

        for seed_idx, seed in enumerate(seeds):
            # Trouver la cellule la plus proche de ce seed
            min_dist = float("inf")
            closest_cell = None

            for cell in cells_set:
                dist_sq = (cell[0] - seed[0]) ** 2 + (cell[1] - seed[1]) ** 2
                if dist_sq < min_dist:
                    min_dist = dist_sq
                    closest_cell = cell

            if closest_cell:
                assignment[closest_cell] = seed_idx
                # Priority queue : (distance au seed, x, y, seed_idx)
                heapq.heappush(priority_queue, (0, closest_cell[0], closest_cell[1], seed_idx))

        # BFS simultané depuis tous les seeds
        while priority_queue:
            dist, x, y, seed_idx = heapq.heappop(priority_queue)

            current_cell = (x, y)

            # Si cette cellule a déjà été assignée à un autre seed, on skip
            if assignment.get(current_cell) != seed_idx and current_cell in assignment:
                continue

            # Explorer les voisins 4-connexes
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                neighbor = (x + dx, y + dy)

                # Vérifier que le voisin est dans l'ensemble et pas encore assigné
                if neighbor in cells_set and neighbor not in assignment:
                    # Calculer la distance au seed
                    seed = seeds[seed_idx]
                    new_dist = (neighbor[0] - seed[0]) ** 2 + (neighbor[1] - seed[1]) ** 2

                    # Assigner et ajouter à la queue
                    assignment[neighbor] = seed_idx
                    heapq.heappush(priority_queue, (new_dist, neighbor[0], neighbor[1], seed_idx))

        # Convertir en format de sortie : seed_idx -> list of cells
        result = defaultdict(list)
        for cell, seed_idx in assignment.items():
            result[seed_idx].append(cell)

        return result

    def _reconstruct_tiles(self, water_groups, land_tiles):
        """
        Reconstruit les tuiles (terre + eau fusionnée).

        Args:
            water_groups: Mapping seed_index -> list of cells
            land_tiles: Liste des tuiles de terre existantes
        """
        new_tiles = {}
        next_id = 0

        # Terres (on garde les objets Tile existants)
        for tile in sorted(land_tiles, key=lambda t: t.id):
            tile.id = next_id
            for x, y in tile.cells:
                self.grid[y][x] = next_id
            new_tiles[next_id] = tile
            next_id += 1

        # Mers fusionnées
        for s_idx, cells in water_groups.items():
            if not cells:
                continue
            w_tile = Tile(next_id, cells)
            w_tile.biome = Biome.WATER
            for x, y in cells:
                self.grid[y][x] = next_id
                self.biomes[y][x] = Biome.WATER
            new_tiles[next_id] = w_tile
            next_id += 1

        self.tiles = new_tiles

    # Méthodes du pipeline de génération

    def _build_neighbors(self):
        """
        Construit le graphe de voisinage entre provinces.

        Deux provinces sont voisines si au moins une de leurs cellules est adjacente latéralement ou diagonalement.

        Ce graphe est essentiel pour :
        - pathfinding
        - gameplay stratégique
        - diffusion (culture, ressources, etc.)
        """
        for y in range(self.height):
            for x in range(self.width):
                id_ = self.grid[y][x]

                if id_ is None:
                    print(f"   ({x,y}) cell is None, check the assignation step")
                    continue

                for nx, ny in self._neighbors(x, y):
                    nid = self.grid[ny][nx]
                    if (
                        nid != id_
                        and id_ in self.tiles
                        and self.tiles[id_] is not None
                        and nid in self.tiles
                        and self.tiles[nid] is not None
                    ):
                        self.tiles[id_].neighbors.add(nid)

    def _neighbors(self, x, y):
        """
        Générateur des 8 coordonnées adjacentes à un point. On considère aussi comme adjacente deux
        provinces ne partageant qu'un sommet commun.

        Args:
            x (int): Coordonnée X d'origine.
            y (int): Coordonnée Y d'origine.
        Yields:
            Tuple[int, int]: Coordonnées valides à l'intérieur des limites de la carte.
        """
        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
            nx, ny = x + dx, y + dy
            if 0 <= nx < self.width and 0 <= ny < self.height:
                yield nx, ny

    def _validate_integrity(self):
        """
        Vérifie que chaque cellule de la grille correspond à une tuile valide et que les tuiles
        référencées contiennent bien ces cellules.
        Cette validation est cruciale pour éviter les incohérences qui pourraient causer des bugs
        difficiles à diagnostiquer plus tard dans le pipeline de génération ou lors du gameplay.
        """
        for y in range(self.height):
            for x in range(self.width):
                tid = self.grid[y][x]
                if tid is None:
                    raise RuntimeError(f"Cell ({x},{y}) has no tile")

                if (x, y) not in self.tiles[tid].cells:
                    raise RuntimeError(f"Inconsistency: cell ({x},{y}) not in tile {tid}")
