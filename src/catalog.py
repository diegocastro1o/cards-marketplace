"""Carga los jugadores del catálogo y los agrupa por rareza."""

from pathlib import Path

from models import CardRarity, Player
from utils.persistence import load_json

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog.json"


def load_catalog(path: Path = CATALOG_PATH) -> dict[CardRarity, list[Player]]:
    """Convierte el catálogo JSON en listas de jugadores por rareza."""
    missing = object()
    data = load_json(path, missing)
    if data is missing:
        raise FileNotFoundError(f"No se encontró el catálogo: {path}")
    if not isinstance(data, dict):
        raise ValueError("El catálogo debe ser un objeto agrupado por rareza.")

    return {
        CardRarity(rarity): [Player(**record) for record in players]
        for rarity, players in data.items()
    }
