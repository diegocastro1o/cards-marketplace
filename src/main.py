"""Punto de entrada por consola para el mercado de cartas."""

from collections.abc import Sequence
from datetime import date
from random import Random

from app_state import load_market, load_users, save_market
from catalog import load_catalog
from models import (
    BronzePack,
    Card,
    CardDrawer,
    CardExchange,
    GoldPack,
    Market,
    MarketListing,
    Pack,
    PackOpening,
    SilverPack,
    User,
)


PACK_NAMES = {"bronze": "Bronce", "silver": "Plata", "gold": "Oro"}


def show_cards(cards: Sequence[Card]) -> None:
    if not cards:
        print("Todavía no hay cartas.")
        return
    for card in cards:
        print(f"  - {card.full_name} ({card.rarity.value})")


def choose_pack(packs: list[Pack]) -> Pack | None:
    options = {str(number): pack for number, pack in enumerate(packs, start=1)}
    print("\nSobres disponibles:")
    for option, pack in options.items():
        print(
            f"  {option}. {PACK_NAMES[pack.type]} · {pack.card_count} cartas"
            f" · {pack.price} monedas"
        )
    print("  0. Volver")

    while True:
        choice = input("Elegí un sobre: ").strip()
        if choice == "0":
            return None
        if choice in options:
            return options[choice]
        print("Opción inválida.")


def open_pack(market: Market, user: User, packs: list[Pack], drawer: CardDrawer) -> bool:
    if user.free_packs_remaining:
        print("Tu próxima apertura es gratuita.")
    pack = choose_pack(packs)
    if pack is None:
        return False

    previous_balance = user.balance
    try:
        cards = market.open_pack(user, pack, drawer, date.today().isoformat())
    except ValueError as error:
        print(f"No se pudo abrir el sobre: {error}")
        return False

    cost = previous_balance - user.balance
    print(f"\nSobre de {PACK_NAMES[pack.type].lower()} abierto · costo: {cost} monedas")
    show_cards(cards)
    return True


def show_history(market: Market) -> None:
    print("\nHistorial de operaciones")
    history = market.get_history()
    if not history:
        print("Todavía no hay operaciones.")
        return
    for operation in history:
        if isinstance(operation, PackOpening):
            pack_name = PACK_NAMES[operation.pack_type]
            print(
                f"  - {operation.occurred_at} · {pack_name}"
                f" · {operation.paid_amount} monedas"
            )
        elif isinstance(operation, CardExchange):
            print(
                f"  - {operation.occurred_at} · Intercambio entre usuarios"
                f" {operation.first_user_id} y {operation.second_user_id}"
                f" · {operation.first_card_id} por {operation.second_card_id}"
            )
        else:
            print(f"  - {operation.occurred_at} · {operation.type}")


def listing_description(listing: MarketListing) -> str:
    return (
        f"{listing.card.full_name} ({listing.card.rarity.value})"
        f" · Vendedor: {listing.seller.user_name} · {listing.price} monedas"
    )


def show_listings(market: Market) -> None:
    print("\nPublicaciones activas")
    listings = market.get_active_listings()
    if not listings:
        print("No hay publicaciones activas.")
        return

    for listing in listings:
        print(f"  - {listing_description(listing)}")


def publish_card(market: Market, user: User) -> None:
    inventory = user.inventory
    if not inventory:
        print("No tenés cartas para publicar.")
        return

    options = {str(number): card for number, card in enumerate(inventory, start=1)}
    print("\nElegí una carta de tu inventario:")
    for option, card in options.items():
        print(f"  {option}. {card.full_name} ({card.rarity.value})")
    print("  0. Volver")

    while True:
        choice = input("Elegí una carta: ").strip()
        if choice == "0":
            return
        if choice in options:
            card = options[choice]
            break
        print("Opción inválida.")

    try:
        price = int(input("Precio en monedas: ").strip())
    except ValueError:
        print("El precio debe ser un entero positivo.")
        return

    try:
        listing = market.publish_card(user, card, price)
    except ValueError as error:
        print(f"No se pudo publicar la carta: {error}")
        return

    print(f"Publicaste a {listing.card.full_name} por {listing.price} monedas.")


def buy_card(market: Market, user: User) -> bool:
    listings = [
        listing for listing in market.get_active_listings()
        if listing.seller.user_id != user.user_id
    ]
    if not listings:
        print("No hay publicaciones de otros usuarios para comprar.")
        return False

    options = {str(number): listing for number, listing in enumerate(listings, start=1)}
    print("\nCartas disponibles para comprar:")
    for option, listing in options.items():
        print(f"  {option}. {listing_description(listing)}")
    print("  0. Volver")

    while True:
        choice = input("Elegí una publicación: ").strip()
        if choice == "0":
            return False
        if choice in options:
            listing = options[choice]
            break
        print("Opción inválida.")

    try:
        market.buy_card(user, listing, date.today().isoformat())
    except ValueError as error:
        print(f"No se pudo comprar la carta: {error}")
        return False

    print(f"Compraste a {listing.card.full_name} por {listing.price} monedas.")
    return True


def choose_card(user: User) -> Card | None:
    """Selecciona un ejemplar del inventario sin modificarlo."""
    options = {str(n): card for n, card in enumerate(user.inventory, start=1)}
    if not options:
        print(f"{user.user_name} no tiene cartas para intercambiar.")
        return None
    print(f"\nInventario de {user.user_name}:")
    for option, card in options.items():
        print(f"  {option}. {card.full_name} ({card.rarity.value})")
    print("  0. Volver")
    while True:
        choice = input("Elegí una carta: ").strip()
        if choice == "0":
            return None
        if choice in options:
            return options[choice]
        print("Opción inválida.")


def exchange_cards(market: Market, user: User, users: list[User]) -> bool:
    others = [other for other in users if other.user_id != user.user_id]
    if not others:
        print("No hay otros usuarios para intercambiar.")
        return False
    second = choose_user(others, cancel_label="Volver")
    if second is None:
        return False
    first_card = choose_card(user)
    if first_card is None:
        return False
    second_card = choose_card(second)
    if second_card is None:
        return False
    print(
        f"{user.user_name} entrega {first_card.full_name};"
        f" {second.user_name} entrega {second_card.full_name}."
    )
    if input("¿Ambos aceptan el intercambio? (s/n): ").strip().lower() != "s":
        print("Intercambio cancelado.")
        return False
    try:
        market.exchange_cards(user, first_card, second, second_card, date.today().isoformat())
    except ValueError as error:
        print(f"No se pudo intercambiar: {error}")
        return False
    print("Intercambio completado.")
    return True


def save_progress(users: list[User], market: Market) -> None:
    try:
        save_market(users, market)
    except (OSError, ValueError) as error:
        print(f"No se pudo guardar el progreso: {error}")


def choose_user(users: list[User], *, cancel_label: str = "Salir") -> User | None:
    options = {str(number): user for number, user in enumerate(users, start=1)}
    print("\nUsuarios disponibles:")
    for option, user in options.items():
        print(f"  {option}. {user.user_name} · {user.balance} monedas")
    print(f"  0. {cancel_label}")

    while True:
        choice = input("Elegí un usuario: ").strip()
        if choice == "0":
            return None
        if choice in options:
            return options[choice]
        print("Opción inválida.")


def main() -> None:
    try:
        catalog = load_catalog()
    except (OSError, ValueError, TypeError) as error:
        print(f"No se pudo cargar el catálogo: {error}")
        return

    try:
        users = load_users()
    except (OSError, ValueError) as error:
        print(f"No se pudieron cargar los usuarios: {error}")
        return

    packs: list[Pack] = [BronzePack(), SilverPack(), GoldPack()]
    try:
        market = load_market(catalog, users, packs)
    except (OSError, ValueError) as error:
        print(f"No se pudo cargar el mercado: {error}")
        return
    drawer = CardDrawer(Random())

    print("Champions League Cards Marketplace")
    print("Las operaciones, las publicaciones y el historial se guardan automáticamente.")
    try:
        user = choose_user(users)
        if user is None:
            print("Hasta la próxima.")
            return
        while True:
            print(f"\n{user.user_name} · Saldo: {user.balance} monedas")
            print(f"Sobres gratuitos disponibles: {user.free_packs_remaining}")
            print(
                "1. Abrir un sobre\n2. Ver inventario\n3. Ver historial\n"
                "4. Ver publicaciones\n5. Publicar carta\n6. Cambiar de usuario\n"
                "7. Comprar carta\n8. Intercambiar cartas\n0. Salir"
            )
            choice = input("Elegí una opción: ").strip()
            if choice == "1":
                if open_pack(market, user, packs, drawer):
                    save_progress(users, market)
            elif choice == "2":
                inventory = user.inventory
                print(f"\nInventario ({len(inventory)} cartas)")
                show_cards(inventory)
            elif choice == "3":
                show_history(market)
            elif choice == "4":
                show_listings(market)
            elif choice == "5":
                publish_card(market, user)
                save_progress(users, market)
            elif choice == "6":
                selected_user = choose_user(users, cancel_label="Volver")
                if selected_user is not None:
                    user = selected_user
            elif choice == "7":
                if buy_card(market, user):
                    save_progress(users, market)
            elif choice == "8":
                if exchange_cards(market, user, users):
                    save_progress(users, market)
            elif choice == "0":
                break
            else:
                print("Opción inválida.")
    except (EOFError, KeyboardInterrupt):
        print()
    print("Hasta la próxima.")


if __name__ == "__main__":
    main()
