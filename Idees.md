
# Game Design Document : Projet 4X

Ce document détaille les spécifications techniques et de gameplay pour notre 4X au tour par tour.

## 1. Identité et Univers
### Propositions de nom
**Imperium Novum**

### Lore
Vous êtes le suzerain exilé d'un royaume lointain. Vous arrivez dans un monde barbares, en des terres jusque là jamais explorées avancée. Votre objectif est de reconstruire votre empire à travers l'exploration, la conquête, la diplomatie et la science. Chaque décision façonne le destin de votre peuple et l'équilibre du pouvoir mondial.


---

## 2. Génération de la Carte
Le monde est généré de manière entièrement **déterministe** via une graine (seed).

* **Géométrie :** Grille rectangulaire basée sur un algorithme de **Voronoï** combiné à un **Poisson Disk Sampling** pour une répartition organique des cellules.
* **Biomes :** Distribution via un **Bruit de Perlin**. Chaque biome influence les ressources et le gameplay :
    * **Plaine :** Bonus nourriture.
    * **Eau :** Obstacle ou transport.
    * **Montagne :** Bonus pierre/fer, bloque la vision.
    * **Forêt :** Bonus bois, modificateur de défense.
    * **Désert :** Malus de déplacement/survie.

---

## 3. Mécaniques de Combat et Unités

### Formule de Dégâts
Les dégâts sont calculés selon la formule suivante :

`damage =(attack - defense * terrain_modifier) * type_modifier * hp_ratio`

### Types d'Unités & Équilibre (Triangle d'Acier)
* **Soldat (Infanterie) :** Efficace contre la Cavalerie.
* **Archer :** Efficace contre l'Infanterie.
* **Cavalier :** Efficace contre les Archers.
* **Colon :** Expansion territoriale.
* **Artillerie :** Siège et dégâts de zone.
* **Avion :** (Optionnel) Unité de fin de jeu, équilibrage complexe.

### Systèmes de Déplacement
* **Pathfinding :** Algorithme A\*.
* **Zone de Contrôle (ZoC) :** Les unités ennemies ralentissent ou bloquent le passage adjacent.
* **Logistique :** Système d'attrition si l'unité dépasse sa portée de ravitaillement (extensible via les routes, dépend des villes).

---

## 4. Économie et Infrastructures

### Ressources
1.  **Or :** Entretien des unités et financement de la science.
2.  **Nourriture :** Croissance de la population.
3.  **Matériaux :** Bois, Pierre, Fer (peuvent être simplifiés en un score unique de **Production** en phase alpha).

### Aménagements de Province (1 slot par case + routes)
* **Ferme :** Boost de nourriture.
* **Mine :** Extraction d'or, pierre ou fer.
* **Caserne :** Production d'unités militaires.
* **Route :** Divise le coût de déplacement par 2, bonus économique vers la capitale.
* **Fort :** Bloque le mouvement ennemi dans les cases adjacentes (mécanique type *Europa Universalis*).

### Croissance et Population
* **Calcul :** Si `FoodSurplus / Population > Seuil`, alors la population augmente.
* **Effets :** Augmente la production et les revenus fiscaux.

---

## 5. Arbre de Technologies
La science est générée par des **Universités** financées par l'or.
* **Branches :** Militaire, Économie (ressources/terrain), Exploration & Diplomatie.
* **Paramètres :** Coût croissant, temps de recherche en tours, prérequis de dépendance.

---

## 6. Intelligence Artificielle
L'IA suit un cycle de vie adaptatif :
* **Early Game :** Focus expansion.
* **Mid Game :** Focus optimisation économique.
* **Late Game :** Focus militaire et victoire.
* **Logique :** Arbre de décision avec pondération dynamique selon l'état du royaume (avantage militaire → agression).

---

## 7. Interface et UX
* **Fog of War (FOW) :** Brouillard de guerre classique.
* **Terra Incognita (TI) :** Zones non explorées.
* **Zone d'Influence :** Rayon de visibilité autour des villes qui croît avec leur développement.
* **HUD :** Panneau de ressources permanent, infobulles (tooltips) au survol des cases, statistiques détaillées à la sélection.

---

## 8. Conditions de Victoire
* **Domination :** Élimination militaire des rivaux.
* **Richesse :** Atteindre un seuil critique de trésorerie/PIB.
* **Technologie :** Compléter l'arbre de recherche.

---

## 9. Objectifs Secondaires ("Si on se chauffe")
* **Événements Dynamiques :** Âges d'or, révoltes, famines, tempêtes.
* **Biomes Évolutifs :** La forêt peut brûler (devient plaine), le désert s'étend avec le vent. (on verra)
* **Multijoueur :** Mode LAN.
