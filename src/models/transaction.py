"""Registros inmutables con identificadores y fechas recibidos desde afuera."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from models.card import Card


@dataclass(frozen=True)
class Transaction(ABC):
    """Datos comunes de una operación completada."""

    operation_id: str
    occurred_at: str

    @property
    @abstractmethod
    def type(self) -> str:
        """Identifica el tipo de operación registrada."""


@dataclass(frozen=True)
class PackOpening(Transaction):
    """Resultado de una apertura, sin repetir el sorteo al consultar el historial."""

    user_id: int
    pack_type: str
    paid_amount: int
    received_cards: tuple[Card, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "received_cards", tuple(self.received_cards))

    @property
    def type(self) -> str:
        return "pack_opening"


@dataclass(frozen=True)
class CardSale(Transaction):
    """Participantes e importes de una venta completada."""

    buyer_id: int
    seller_id: int
    card_id: str
    price: int
    commission: int

    @property
    def type(self) -> str:
        return "card_sale"


@dataclass(frozen=True)
class CardExchange(Transaction):
    """Participantes y ejemplares de un intercambio completado."""

    first_user_id: int
    second_user_id: int
    first_card_id: str
    second_card_id: str

    @property
    def type(self) -> str:
        return "card_exchange"
