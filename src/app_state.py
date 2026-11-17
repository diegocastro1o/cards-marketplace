"""Lee y guarda los usuarios y sus inventarios."""

from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import NotRequired, TypedDict

from models.card import Card, CardRarity, CardTrait, Player, PlayerPosition
from models.user import User
from models.listing import MarketListing
from models.market import Market
from models.pack import Pack
from models.transaction import CardExchange, CardSale, PackOpening
from utils.persistence import load_json, save_json

APP_STATE_PATH = Path(__file__).resolve().parent.parent / "data" / "app_state.json"


class CardRecord(TypedDict):
    """Campos de un ejemplar en el JSON de arranque."""

    card_id: str
    full_name: str
    position: str
    rarity: str
    trait: str | None


class UserRecord(TypedDict):
    """Campos de un usuario en el JSON de arranque."""

    user_id: int
    username: str
    balance: int
    inventory: list[CardRecord]
    free_packs_remaining: NotRequired[int]
    packs_opened_today: NotRequired[int]
    last_opening_day: NotRequired[str | None]


def load_users(path: Path = APP_STATE_PATH) -> list[User]:
    """Crea usuarios a partir de los perfiles del archivo de arranque."""
    missing = object()
    data = load_json(path, missing)
    if data is missing:
        raise FileNotFoundError(f"No se encontró el estado inicial: {path}")
    if not isinstance(data, dict) or not isinstance(data.get("users"), list):
        raise ValueError("El estado inicial debe contener una lista de usuarios.")
    if not data["users"]:
        raise ValueError("El estado inicial no contiene usuarios.")

    return _users_from_records(data["users"])


def _users_from_records(profiles: list[UserRecord]) -> list[User]:
    """Valida y convierte perfiles actuales o de la base histórica."""
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("Los perfiles deben ser una lista no vacía.")
    users: list[User] = []
    user_ids: set[int] = set()
    card_ids: set[str] = set()
    for profile in profiles:
        if not isinstance(profile, dict):
            raise ValueError("Cada perfil debe ser un objeto.")
        user_id = profile.get("user_id")
        username = profile.get("username")
        if type(user_id) is not int or user_id <= 0 or user_id in user_ids:
            raise ValueError("Los identificadores deben ser enteros positivos y únicos.")
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Cada usuario debe tener un nombre.")
        last_opening_day = profile.get("last_opening_day")
        if last_opening_day is not None and not isinstance(last_opening_day, str):
            raise ValueError(f"La última apertura de {username} debe ser una fecha ISO.")
        user = User(
            user_id, username, profile["balance"],
            free_packs_remaining=profile.get("free_packs_remaining", User.INITIAL_FREE_PACKS),
            packs_opened_today=profile.get("packs_opened_today", 0),
            last_opening_day=(
                date.fromisoformat(last_opening_day) if last_opening_day is not None else None
            ),
        )

        inventory = profile.get("inventory")
        if not isinstance(inventory, list):
            raise ValueError(f"El inventario de {username} debe ser una lista.")

        for record in inventory:
            if not isinstance(record, dict):
                raise ValueError(f"Cada carta del inventario de {username} debe ser un objeto.")
            card_id = record.get("card_id")
            full_name = record.get("full_name")
            if not isinstance(card_id, str) or not card_id.strip():
                raise ValueError(f"Hay una carta sin identificador válido en el inventario de {username}.")
            if not isinstance(full_name, str) or not full_name.strip():
                raise ValueError(f"El ejemplar {card_id} debe tener un nombre.")
            if card_id in card_ids:
                raise ValueError(f"El ejemplar {card_id} está repetido en los inventarios.")

            try:
                trait = record["trait"]
                card = Card(
                    card_id=card_id,
                    full_name=full_name,
                    position=PlayerPosition(record["position"]),
                    rarity=CardRarity(record["rarity"]),
                    trait=CardTrait(trait) if trait is not None else None,
                )
            except KeyError as error:
                raise ValueError(f"Al ejemplar {card_id} le falta el campo {error.args[0]}.") from error
            user.add_card(card)
            card_ids.add(card_id)

        users.append(user)
        user_ids.add(user_id)

    return users


def _card_to_record(card: Card) -> CardRecord:
    return {
        "card_id": card.card_id,
        "full_name": card.full_name,
        "position": card.position.value,
        "rarity": card.rarity.value,
        "trait": card.trait.value if card.trait is not None else None,
    }


def save_users(users: list[User], path: Path = APP_STATE_PATH) -> None:
    """Actualiza los perfiles sin reemplazar otras secciones del JSON."""
    data = load_json(path, {"listings": []})
    if not isinstance(data, dict):
        raise ValueError("El estado guardado debe ser un objeto.")

    data["users"] = _users_to_records(users)
    save_json(data, path)


def _users_to_records(users: list[User]) -> list[UserRecord]:
    profiles: list[UserRecord] = []
    for user in users:
        last_day = user.last_opening_day
        profiles.append({
            "user_id": user.user_id,
            "username": user.user_name,
            "balance": user.balance,
            "inventory": [_card_to_record(card) for card in user.inventory],
            "free_packs_remaining": user.free_packs_remaining,
            "packs_opened_today": user.packs_opened_today,
            "last_opening_day": last_day.isoformat() if last_day is not None else None,
        })
    return profiles


def _record_to_card(record: CardRecord) -> Card:
    return Card(
        card_id=record["card_id"], full_name=record["full_name"],
        position=PlayerPosition(record["position"]),
        rarity=CardRarity(record["rarity"]),
        trait=None if record["trait"] is None else CardTrait(record["trait"]),
    )


def save_market(
    users: list[User], market: Market, path: Path = APP_STATE_PATH,
) -> None:
    """Guarda usuarios, publicaciones activas e historial en un solo reemplazo."""
    data = load_json(path, {})
    if not isinstance(data, dict):
        raise ValueError("El estado guardado debe ser un objeto.")
    history = []
    for transaction in market.get_history():
        record = asdict(transaction)
        record["type"] = transaction.type
        if isinstance(transaction, PackOpening):
            record["received_cards"] = [
                _card_to_record(card) for card in transaction.received_cards
            ]
        history.append(record)
    data.update({
        "users": _users_to_records(users),
        "listings": [
            {"seller_id": listing.seller.user_id,
             "card_id": listing.card.card_id, "price": listing.price}
            for listing in market.get_active_listings()
        ],
        "transactions": history,
        "history_base": {
            "after_operations": market.history_start,
            "users": _users_to_records(market.get_history_base()),
        },
    })
    save_json(data, path)


def load_market(
    catalog: dict[CardRarity, list[Player]], users: list[User], packs: list[Pack],
    path: Path = APP_STATE_PATH,
) -> Market:
    """Recupera las publicaciones y el historial; admite estados anteriores sin ellos."""
    data = load_json(path, {})
    if not isinstance(data, dict):
        raise ValueError("El estado guardado debe ser un objeto.")
    transactions = []
    operation_ids = set()
    try:
        records = data.get("transactions", [])
        listings = data.get("listings", [])
        if not isinstance(records, list) or not isinstance(listings, list):
            raise ValueError("Las publicaciones y las transacciones deben ser listas.")
        types = {
            "pack_opening": PackOpening,
            "card_sale": CardSale,
            "card_exchange": CardExchange,
        }
        for record in records:
            values = record.copy()
            transaction_class = types[values.pop("type")]
            date.fromisoformat(values["occurred_at"])
            operation_id = values["operation_id"]
            if not isinstance(operation_id, str) or not operation_id or operation_id in operation_ids:
                raise ValueError("Los identificadores de operaciones deben ser únicos y no vacíos.")
            operation_ids.add(operation_id)
            if transaction_class is PackOpening:
                values["received_cards"] = tuple(
                    _record_to_card(card) for card in values["received_cards"]
                )
            transactions.append(transaction_class(**values))

        baseline = data.get("history_base")
        history_base = None
        history_start = None
        if baseline is not None:
            if not isinstance(baseline, dict):
                raise ValueError("La base histórica debe ser un objeto.")
            history_base = _users_from_records(baseline["users"])
            history_start = baseline["after_operations"]
        market = Market(
            catalog, users=users, packs=packs, transactions=transactions,
            history_base=history_base, history_start=history_start,
        )
        by_id = {user.user_id: user for user in users}
        for record in listings:
            seller = by_id[record["seller_id"]]
            card = next(
                card for card in seller.inventory if card.card_id == record["card_id"]
            )
            market.publish_card(seller, card, record["price"])
        return market
    except (KeyError, TypeError, AttributeError, StopIteration) as error:
        raise ValueError("El historial o las publicaciones guardadas no son válidos.") from error
