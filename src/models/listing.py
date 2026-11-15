"""Publicaciones de cartas disponibles para la venta."""

from models.card import Card
from models.user import User


class MarketListing:
    """Representa una oferta; Market coordina la compraventa."""

    def __init__(self, card: Card, seller: User, price: int):
        if type(price) is not int or price <= 0:
            raise ValueError("El precio debe ser un entero positivo.")
        self.__card = card
        self.__seller = seller
        self.__price = price
        self.__active = True

    @property
    def card(self) -> Card:
        return self.__card

    @property
    def seller(self) -> User:
        return self.__seller

    @property
    def price(self) -> int:
        return self.__price

    @property
    def active(self) -> bool:
        return self.__active

    def close(self) -> None:
        if not self.__active:
            raise ValueError("La publicación ya está cerrada.")
        self.__active = False
