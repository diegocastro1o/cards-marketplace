"""Coordinación de las operaciones y del historial del mercado."""

from collections.abc import Callable
from copy import deepcopy
from datetime import date
from uuid import UUID, uuid4

from utils.calculations import calculate_sale_amounts
from models.card import Card, CardRarity, Player
from models.exceptions import InsufficientFundsError
from models.listing import MarketListing
from models.pack import CardDrawer, Pack
from models.transaction import CardExchange, CardSale, PackOpening, Transaction
from models.user import User
from history import rebuild_users


class Market:
    """Reúne los modelos y declara las operaciones del UML."""

    def __init__(
        self, catalog: dict[CardRarity, list[Player]], users: list[User] | None = None,
        listings: list[MarketListing] | None = None, packs: list[Pack] | None = None,
        *, id_factory: Callable[[], UUID] = uuid4,
        transactions: list[Transaction] | None = None,
        history_base: list[User] | None = None,
        history_start: int | None = None,
    ):
        self.__catalog = {rarity: players.copy() for rarity, players in catalog.items()}
        self.__users = [] if users is None else users.copy()
        self.__listings = [] if listings is None else listings.copy()
        self.__packs = [] if packs is None else packs.copy()
        self.__transactions = [] if transactions is None else transactions.copy()
        self.__id_factory = id_factory
        if history_base is None:
            if history_start is not None:
                raise ValueError("Falta la base histórica indicada.")
            self.__history_base = deepcopy(self.__users)
            self.__history_start = len(self.__transactions)
        else:
            if type(history_start) is not int or not 0 <= history_start <= len(self.__transactions):
                raise ValueError("El inicio de la reconstrucción no es válido.")
            if {u.user_id for u in history_base} != {u.user_id for u in self.__users}:
                raise ValueError("La base histórica no corresponde a los usuarios actuales.")
            self.__history_base = deepcopy(history_base)
            self.__history_start = history_start

    def open_pack(
        self, buyer: User, pack: Pack, drawer: CardDrawer, day: str
    ) -> list[Card]:
        """Abre un sobre y registra las cartas entregadas al comprador."""
        if buyer not in self.__users:
            raise ValueError("El comprador no está registrado en el mercado.")

        if not buyer.can_open_pack(day):
            raise ValueError("No se puede abrir otro sobre para esa fecha.")

        used_free_pack = buyer.free_packs_remaining > 0
        paid_amount = 0 if used_free_pack else pack.price
        if paid_amount > buyer.balance:
            raise InsufficientFundsError("No existen fondos suficientes.")

        cards = pack.open(self.__catalog, drawer)
        card_ids = {card.card_id for card in cards}
        if len(card_ids) != len(cards) or any(
            user.has_card(card) for user in (buyer, *self.__users) for card in cards
        ):
            raise ValueError("El sobre contiene identificadores de cartas repetidos.")

        opening = PackOpening(
            operation_id=str(self.__id_factory()),
            occurred_at=day,
            user_id=buyer.user_id,
            pack_type=pack.type,
            paid_amount=paid_amount,
            received_cards=tuple(cards),
        )

        if paid_amount:
            buyer.debit(paid_amount)
        for card in cards:
            buyer.add_card(card)
        buyer.register_pack_opening(day, used_free_pack)
        self.__transactions.append(opening)
        return cards

    def publish_card(self, seller: User, card: Card, price: int) -> MarketListing:
        """Publica un ejemplar sin cambiar su propietario ni los saldos."""
        if seller not in self.__users:
            raise ValueError("El vendedor no está registrado en el mercado.")

        owned_card = next(
            (owned for owned in seller.inventory if owned.card_id == card.card_id),
            None,
        )
        if owned_card is None:
            raise ValueError("El ejemplar no pertenece al vendedor.")

        if any(
            listing.active and listing.card.card_id == owned_card.card_id
            for listing in self.__listings
        ):
            raise ValueError("El ejemplar ya tiene una publicación activa.")

        listing = MarketListing(owned_card, seller, price)
        self.__listings.append(listing)
        return listing

    def get_active_listings(self) -> list[MarketListing]:
        """Devuelve las publicaciones que siguen disponibles."""
        return [listing for listing in self.__listings if listing.active]

    def buy_card(self, buyer: User, listing: MarketListing, day: str) -> None:
        """Completa y registra una compra después de validar la operación."""
        date.fromisoformat(day)
        if buyer not in self.__users:
            raise ValueError("El comprador no está registrado en el mercado.")
        if listing not in self.__listings or not listing.active:
            raise ValueError("La publicación no está disponible en este mercado.")

        seller = listing.seller
        card = listing.card
        if seller not in self.__users:
            raise ValueError("El vendedor no está registrado en el mercado.")
        if buyer.user_id == seller.user_id:
            raise ValueError("No podés comprar tu propia publicación.")
        if not seller.has_card(card):
            raise ValueError("El ejemplar ya no pertenece al vendedor.")
        if buyer.has_card(card):
            raise ValueError("El comprador ya tiene ese ejemplar.")
        if buyer.balance < listing.price:
            raise InsufficientFundsError("No existen fondos suficientes.")

        price = listing.price
        commission, seller_amount = calculate_sale_amounts(price)
        sale = CardSale(
            operation_id=str(self.__id_factory()),
            occurred_at=day,
            buyer_id=buyer.user_id,
            seller_id=seller.user_id,
            card_id=card.card_id,
            price=price,
            commission=commission,
        )

        buyer.debit(price)
        seller.credit(seller_amount)
        seller.remove_card(card)
        buyer.add_card(card)
        listing.close()
        self.__transactions.append(sale)

    def exchange_cards(
        self, first: User, first_card: Card, second: User, second_card: Card,
        day: str,
    ) -> None:
        """Intercambia dos ejemplares y registra la operación."""
        date.fromisoformat(day)
        if first not in self.__users or second not in self.__users:
            raise ValueError("Ambos usuarios deben estar registrados.")
        if first.user_id == second.user_id:
            raise ValueError("No podés intercambiar contigo mismo.")
        if first_card.card_id == second_card.card_id:
            raise ValueError("Deben ser dos ejemplares distintos.")
        if not first.has_card(first_card):
            raise ValueError("La primera carta no pertenece al primer usuario.")
        if not second.has_card(second_card):
            raise ValueError("La segunda carta no pertenece al segundo usuario.")
        if second.has_card(first_card) or first.has_card(second_card):
            raise ValueError("Un destinatario ya posee el ejemplar que recibiría.")

        offered_ids = {first_card.card_id, second_card.card_id}
        if any(
            listing.active and listing.card.card_id in offered_ids
            for listing in self.__listings
        ):
            raise ValueError("No se pueden intercambiar cartas publicadas.")

        first_owned = next(
            card for card in first.inventory if card.card_id == first_card.card_id
        )
        second_owned = next(
            card for card in second.inventory if card.card_id == second_card.card_id
        )
        exchange = CardExchange(
            operation_id=str(self.__id_factory()),
            occurred_at=day,
            first_user_id=first.user_id,
            second_user_id=second.user_id,
            first_card_id=first_owned.card_id,
            second_card_id=second_owned.card_id,
        )

        first.remove_card(first_owned)
        second.remove_card(second_owned)
        first.add_card(second_owned)
        second.add_card(first_owned)
        self.__transactions.append(exchange)

    def get_history(self) -> list[Transaction]:
        """Entrega una copia del historial de operaciones completadas."""
        return self.__transactions.copy()

    @property
    def history_start(self) -> int:
        """Cantidad de operaciones anteriores a la base histórica disponible."""
        return self.__history_start

    def get_history_base(self) -> list[User]:
        """Devuelve una copia independiente del punto de partida."""
        return deepcopy(self.__history_base)

    def reconstruct_users(self, operations_ago: int = 0) -> list[User]:
        """Consulta saldos, inventarios y contadores; no cambia la sesión actual."""
        available = len(self.__transactions) - self.__history_start
        if type(operations_ago) is not int or not 0 <= operations_ago <= available:
            raise ValueError("La consulta queda fuera del historial reconstruible.")
        return rebuild_users(
            self.__history_base, self.__transactions[self.__history_start:],
            available - operations_ago,
        )
