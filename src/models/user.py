"""Usuarios, saldos e inventarios del mercado."""

from datetime import date

from models.card import Card
from models.exceptions import InsufficientFundsError


class User:
    """Protege el saldo y la colección de un usuario."""

    INITIAL_FREE_PACKS = 3
    DAILY_PACK_LIMIT = 5

    def __init__(
        self, user_id: int, user_name: str, balance: int = 1000, *,
        free_packs_remaining: int = INITIAL_FREE_PACKS,
        packs_opened_today: int = 0,
        last_opening_day: date | None = None,
    ):
        if type(balance) is not int or balance < 0:
            raise ValueError("El saldo debe ser un entero no negativo.")
        if (
            type(free_packs_remaining) is not int
            or not 0 <= free_packs_remaining <= self.INITIAL_FREE_PACKS
        ):
            raise ValueError("La cantidad de sobres gratuitos no es válida.")
        if (
            type(packs_opened_today) is not int
            or not 0 <= packs_opened_today <= self.DAILY_PACK_LIMIT
            or (last_opening_day is None) != (packs_opened_today == 0)
        ):
            raise ValueError("El contador de aperturas no coincide con el estado diario.")
        self.__user_id = user_id
        self.__user_name = user_name
        self.__balance = balance
        self.__inventory: list[Card] = []
        self.__free_packs_remaining = free_packs_remaining
        self.__packs_opened_today = packs_opened_today
        self.__last_opening_day = last_opening_day

    @property
    def user_id(self) -> int:
        return self.__user_id

    @property
    def user_name(self) -> str:
        return self.__user_name

    @property
    def balance(self) -> int:
        return self.__balance

    @property
    def inventory(self) -> list[Card]:
        """Devuelve una copia para proteger la colección interna."""
        return self.__inventory.copy()

    @property
    def free_packs_remaining(self) -> int:
        return self.__free_packs_remaining

    @property
    def packs_opened_today(self) -> int:
        return self.__packs_opened_today

    @property
    def last_opening_day(self) -> date | None:
        return self.__last_opening_day

    def get_balance(self) -> int:
        return self.__balance

    def debit(self, amount: int) -> None:
        if type(amount) is not int or amount <= 0:
            raise ValueError("El importe debe ser un entero positivo.")
        if amount > self.__balance:
            raise InsufficientFundsError("No existen fondos suficientes.")

        self.__balance -= amount

    def credit(self, amount: int) -> None:
        if type(amount) is not int or amount <= 0:
            raise ValueError("El importe debe ser un entero positivo.")

        self.__balance += amount

    def has_card(self, card: Card) -> bool:
        return any(c.card_id == card.card_id for c in self.__inventory)

    def add_card(self, card: Card) -> None:
        if self.has_card(card):
            raise ValueError("El ejemplar ya está en el inventario.")

        self.__inventory.append(card)

    def remove_card(self, card: Card) -> None:
        for index, owned_card in enumerate(self.__inventory):
            if owned_card.card_id == card.card_id:
                self.__inventory.pop(index)
                return

        raise ValueError("El ejemplar no pertenece al usuario.")

    def can_open_pack(self, day: str) -> bool:
        """Consulta el límite para la fecha indicada sin cambiar el estado."""
        opening_day = date.fromisoformat(day)
        last_day = self.__last_opening_day
        if last_day is None or opening_day > last_day:
            return True
        return opening_day == last_day and self.__packs_opened_today < self.DAILY_PACK_LIMIT

    def register_pack_opening(self, day: str, used_free_pack: bool) -> None:
        """Actualiza los contadores tras una apertura exitosa."""
        if not self.can_open_pack(day):
            raise ValueError("No se puede registrar otra apertura para esa fecha.")
        if used_free_pack and self.__free_packs_remaining == 0:
            raise ValueError("No quedan sobres gratuitos.")

        opening_day = date.fromisoformat(day)
        if opening_day != self.__last_opening_day:
            self.__last_opening_day = opening_day
            self.__packs_opened_today = 0

        self.__packs_opened_today += 1
        if used_free_pack:
            self.__free_packs_remaining -= 1
