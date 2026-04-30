from typing import List
from dataclasses import dataclass, field


@dataclass
class Kingdom:
    """Représente un royaume (joueur humain ou IA indépendante).

    Chaque royaume possède une identité visuelle et, s'il est contrôlé par une IA,
    un dictionnaire de paramètres utilisé par l'arbre de décision pondéré.
    """

    kingdom_id: int
    cities: List[int]
    name: str
    color: tuple  # RGB utilisé pour l'affichage UI

    is_ai: bool = False

    # Paramètres de décision pour l'IA (arbre de décision pondéré).
    # Clés typiques : "aggression", "expansion", "defense", "exploration". (j'en sais rien, j'écris juste ce qui me vient à l'esprit)
    # Valeurs : float dans [0, 1] ; une valeur élevée augmente le poids de ce comportement.
    ai_params: dict = field(default_factory=dict)

    def __repr__(self) -> str:
        kind = "IA" if self.is_ai else "Humain"
        return f"Kingdom({self.kingdom_id}, '{self.name}', {kind})"
