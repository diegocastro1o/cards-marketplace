"""Tipos de sobres y selección ponderada de cartas."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from random import Random
from uuid import UUID, uuid4

from models.card import Card, CardRarity, CardTrait, Player, PlayerPosition


class CardDrawer:
    """Sortea jugadores y asigna UUIDs a sus ejemplares."""

    def __init__(self, rng: Random, id_factory: Callable[[], UUID] = uuid4):
        self.__rng = rng
        self.__id_factory = id_factory

    def draw_card(
        self, catalog: dict[CardRarity, list[Player]], weights: dict[CardRarity, int]
    ) -> Card:
        """Crea un ejemplar nuevo a partir del jugador sorteado."""
        rarity, player = self._select_player(catalog, weights)
        position = PlayerPosition(player.position)
        trait = None if player.trait is None else CardTrait(player.trait)
        return Card(
            card_id=str(self.__id_factory()),
            full_name=player.full_name,
            position=position,
            rarity=rarity,
            trait=trait,
        )

    def _select_player(
        self, catalog: dict[CardRarity, list[Player]], weights: dict[CardRarity, int]
    ) -> tuple[CardRarity, Player]:
        """Sortea la rareza y luego un jugador de ese grupo."""
        if not weights or any(type(w) is not int or w < 0 for w in weights.values()):
            raise ValueError("Los pesos deben ser enteros no negativos.")
        if sum(weights.values()) == 0:
            raise ValueError("Debe existir al menos un peso positivo.")

        players_by_rarity = {
            rarity: catalog.get(rarity, [])
            for rarity, weight in weights.items()
            if weight > 0
        }

        if any(not players for players in players_by_rarity.values()):
            raise ValueError("Hay rarezas con peso positivo sin cartas disponibles.")

        rarities = list(players_by_rarity)
        rarity = self.__rng.choices(
            rarities, weights=[weights[r] for r in rarities], k=1
        )[0]

        return rarity, self.__rng.choice(players_by_rarity[rarity])


class Pack(ABC):
    """Define los datos compartidos y la apertura de un sobre."""

    @abstractmethod
    def __init__(
        self, pack_type: str, price: int,
        rarity_weights: dict[CardRarity, int], card_count: int = 3,
    ):
        if type(price) is not int or price <= 0:
            raise ValueError("El precio debe ser un entero positivo.")
        if type(card_count) is not int or card_count <= 0:
            raise ValueError("La cantidad de cartas debe ser un entero positivo.")
        self.__type = pack_type
        self.__price = price
        self.__card_count = card_count
        self.__rarity_weights = rarity_weights.copy()

    @property
    def type(self) -> str:
        return self.__type

    @property
    def price(self) -> int:
        return self.__price

    @property
    def card_count(self) -> int:
        return self.__card_count

    @property
    def rarity_weights(self) -> dict[CardRarity, int]:
        return self.__rarity_weights.copy()

    def open(
        self, catalog: dict[CardRarity, list[Player]], drawer: CardDrawer
    ) -> list[Card]:
        """Produce cartas; Market se ocupa del cobro y del inventario."""
        return [
            drawer.draw_card(catalog, self.__rarity_weights.copy())
            for _ in range(self.__card_count)
        ]


class BronzePack(Pack):
    """Sobre de bronce con los valores ya definidos en el proyecto."""

    def __init__(self):
        super().__init__("bronze", 200, {
            CardRarity.COMMON: 50,
            CardRarity.RARE: 25,
            CardRarity.EXCEPTIONAL: 15,
            CardRarity.ELITE: 7,
            CardRarity.MASTERCLASS: 2,
            CardRarity.LEGENDARY: 1,
        })


class SilverPack(Pack):
    """Sobre de plata con su propio precio y pesos de rareza."""

    def __init__(self):
        super().__init__("silver", 350, {
            CardRarity.COMMON: 36,
            CardRarity.RARE: 27,
            CardRarity.EXCEPTIONAL: 16,
            CardRarity.ELITE: 12,
            CardRarity.MASTERCLASS: 6,
            CardRarity.LEGENDARY: 3,
        })


class GoldPack(Pack):
    """Sobre de oro con su propio precio y pesos de rareza."""

    def __init__(self):
        super().__init__("gold", 500, {
            CardRarity.COMMON: 50,
            CardRarity.RARE: 25,
            CardRarity.EXCEPTIONAL: 15,
            CardRarity.ELITE: 7,
            CardRarity.MASTERCLASS: 2,
            CardRarity.LEGENDARY: 5,
        })

