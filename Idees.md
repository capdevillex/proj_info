Propositions de noms :
	Imperium Novum
	Krata
	Arkhon

- Carte rectangulaire avec cases à la géométrie créée par l'algo de Voronoï + Poisson disk sampling et "biomisées" avec un bruit de Perlin (entièrement déterministe sur seed)

- Cases avec les modificateurs suivants :
	défense
	attaque
	vision (bloque / porte)
	déplacement (entrée / sortie, coût asymétrique)
	route
	ressources
	supply_limit

- Unités :
	damage = base_damage * (attack / (attack + defense)) * terrain_modifier * (hp / max_hp)
	Déplacement avec A*
	Zone of Control ?

	Soldat
	Colon
	Cavalier
	Archer
	Avion (si on se chauffe, difficile à équilibrer)
	Artillerie

	- Contre-unités :
		cavalerie > archers
		archers > infanterie
		infanterie > cavalerie

- Arbre de technologies:
	Militaire
	Économie (apprivoisement terrain, aprivoisement ressource)
	Exploration / Diplomatie
	coût croissant
	temps de recherche
	prérequis (arbre)
	science produite par des université financées par de l'or (+ programme de recherche inter-cité)

- Ressources :
	Or
	Nourriture
	Bois (constructions)
	Pierre (défense / bâtiments)
	Fer (unités avancées)
	On peut abstraire Bois + Pierre + Fer en Production dans un premier temps
	Chasse ?

- Biomes:
	Plaine
	Eau
	Montagne
	Forêt
	Désert
	Un biome influence les ressources disponibles avec des bonus (forêt → bois, montagne → pierre/fer, plaine → nourriture)

- Par province (1 seul par province, sauf routes, upgradable):
	Ferme = + food
	Mine = + or ou pierre
	Caserne = unités
	Route = cout déplacement / 2
	Fort = interdit le déplacement dans les provinces adjacentes (EU)

- Idées :
	Les unités coûtent de l'or et en consomment à chaque tour (CIV)
	Brouillard de guerre (FOW)
	Terra Incognita (TI)
	Zone d'influence autour des villes : zone sans FOW qui grandi avec le développement de la cité
	Contrôle de territoire, provinces adjacentes = bonus
	Logistique : unités trop loin = malus d'attrition proportionnel au dépassement de la portée de ravitaillement (augmentable avec des routes)
	Routes : réduisent coût déplacement, bonus économique si connecté à capitale (Polytopia)
	Ville : une ville est une province capitale plus sa zone d'influence qui grandi comme dans CIV
	Population : si food_surplus / pop > valeur_arbitraire alors pop++ -> +prod et +taxes
	Events comme dans EU : âge d’or → +prod, révolte → perte province, famine, mauvaise récoltes, etc.

- IA :
	arbre de décision
	pondération des branches en fonction de l'état de son royaume
	expansion aléatoire pondérée
	attaque si avantage
	priorité ressources
	comportement :
		expansion early
		économie midgame
		guerre late

- HUD / UX
	survol case → infos
	sélection unité → stats
	minimap ?
	panneau ressources

- Conditions de victoire :
	domination (militaire)
	richesse (éco)
	technologie (science)

- Si on a le temps et que l'on se chauffe un peu :
	Biomes dynamiques :
	- forêt brûle → devient plaine
	- désert s’étend dans la direction du vent tous les X tours
	Événements aléatoires :
	- famine
	- tempête
	- découverte
