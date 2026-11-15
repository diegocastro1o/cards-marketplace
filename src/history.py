"""Reconstrucción económica sin archivos, reloj, azar ni cambios al mercado."""

from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.transaction import Transaction
    from models.user import User


def rebuild_users(
    initial_users: list[User], transactions: Sequence[Transaction], through: int,
) -> list[User]:
    """Aplica las primeras through operaciones sobre una copia de la base."""
    if type(through) is not int or not 0 <= through <= len(transactions):
        raise ValueError("La cantidad de operaciones no es válida.")
    users = deepcopy(initial_users)
    by_id = {user.user_id: user for user in users}
    if len(by_id) != len(users):
        raise ValueError("La base contiene usuarios repetidos.")
    card_ids = [card.card_id for user in users for card in user.inventory]
    if len(card_ids) != len(set(card_ids)):
        raise ValueError("La base contiene ejemplares repetidos.")

    operation_ids = set()
    for transaction in transactions[:through]:
        if (
            not isinstance(transaction.operation_id, str)
            or not transaction.operation_id
            or transaction.operation_id in operation_ids
        ):
            raise ValueError("El historial contiene identificadores de operación inválidos.")
        operation_ids.add(transaction.operation_id)
        date.fromisoformat(transaction.occurred_at)
        try:
            _apply_transaction(by_id, transaction)
        except (KeyError, StopIteration) as error:
            raise ValueError("El historial referencia un usuario o una carta ausente.") from error
    return users


def _apply_transaction(users: dict[int, User], transaction: Transaction) -> None:
    from models.transaction import CardExchange, CardSale, PackOpening

    if isinstance(transaction, PackOpening):
        user = users[transaction.user_id]
        amount = transaction.paid_amount
        if type(amount) is not int or amount < 0:
            raise ValueError("El importe de una apertura no es válido.")
        free = amount == 0
        if free != (user.free_packs_remaining > 0):
            raise ValueError("La apertura no coincide con los sobres gratuitos disponibles.")
        if not user.can_open_pack(transaction.occurred_at):
            raise ValueError("La apertura excede el límite diario.")
        cards = transaction.received_cards
        if not cards or len({card.card_id for card in cards}) != len(cards):
            raise ValueError("La apertura debe contener ejemplares distintos.")
        if any(owner.has_card(card) for owner in users.values() for card in cards):
            raise ValueError("La apertura duplica un ejemplar existente.")
        if amount:
            user.debit(amount)
        for card in cards:
            user.add_card(card)
        user.register_pack_opening(transaction.occurred_at, free)

    elif isinstance(transaction, CardSale):
        buyer, seller = users[transaction.buyer_id], users[transaction.seller_id]
        if buyer is seller:
            raise ValueError("Una venta debe involucrar dos usuarios distintos.")
        price, commission = transaction.price, transaction.commission
        if (
            type(price) is not int or price <= 0
            or type(commission) is not int or not 0 <= commission < price
        ):
            raise ValueError("Los importes de la venta no son válidos.")
        card = next(card for card in seller.inventory if card.card_id == transaction.card_id)
        if buyer.has_card(card):
            raise ValueError("El comprador ya posee el ejemplar.")
        buyer.debit(price)
        seller.credit(price - commission)
        seller.remove_card(card)
        buyer.add_card(card)

    elif isinstance(transaction, CardExchange):
        first, second = users[transaction.first_user_id], users[transaction.second_user_id]
        if first is second or transaction.first_card_id == transaction.second_card_id:
            raise ValueError("El intercambio debe involucrar usuarios y ejemplares distintos.")
        first_card = next(c for c in first.inventory if c.card_id == transaction.first_card_id)
        second_card = next(c for c in second.inventory if c.card_id == transaction.second_card_id)
        if first.has_card(second_card) or second.has_card(first_card):
            raise ValueError("El intercambio duplicaría un ejemplar.")
        first.remove_card(first_card)
        second.remove_card(second_card)
        first.add_card(second_card)
        second.add_card(first_card)

    else:
        raise ValueError("Tipo de transacción desconocido.")
