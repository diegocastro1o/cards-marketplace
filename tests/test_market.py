"""Pruebas de reproducibilidad, compras e intercambios."""

from datetime import date, timedelta
from random import Random
from unittest import TestCase
from unittest.mock import Mock
from uuid import UUID

from models import (
    BronzePack, Card, CardDrawer, CardExchange, CardRarity, CardSale, Market, MarketListing,
    InsufficientFundsError, PackOpening, Player, PlayerPosition, User,
)

DAY = "2026-11-10"
PRICE = 199


class MarketTests(TestCase):
    def test_failure_after_first_draw_preserves_free_and_paid_pack_state(self) -> None:
        for free_packs in (3, 0):
            with self.subTest(free_packs=free_packs):
                buyer = User(1, "Comprador", 500, free_packs_remaining=free_packs)
                owned = Card("propia", "Jugador propio", PlayerPosition.FORWARD, CardRarity.COMMON)
                buyer.add_card(owned)
                pack = BronzePack()
                operation_ids = Mock()
                market = Market({}, users=[buyer], packs=[pack], id_factory=operation_ids)
                listing = market.publish_card(buyer, owned, 100)
                generated = Card("nueva", "Jugador nuevo", PlayerPosition.DEFENDER, CardRarity.RARE)
                drawer = Mock(spec=CardDrawer)
                drawer.draw_card.side_effect = [
                    generated, ValueError("Fallo al generar la segunda carta."),
                ]

                def snapshot() -> tuple:
                    return (
                        buyer.balance, buyer.inventory, buyer.free_packs_remaining,
                        buyer.packs_opened_today, buyer.last_opening_day,
                        market.get_history(), market.get_active_listings(), listing.active,
                    )

                before = snapshot()
                with self.assertRaisesRegex(ValueError, "segunda carta"):
                    market.open_pack(buyer, pack, drawer, DAY)

                self.assertEqual(drawer.draw_card.call_count, 2)
                self.assertEqual(snapshot(), before)
                self.assertFalse(buyer.has_card(generated))
                operation_ids.assert_not_called()

    def test_paid_pack_with_insufficient_balance_preserves_state(self) -> None:
        pack = BronzePack()
        buyer = User(1, "Comprador", pack.price - 1, free_packs_remaining=0)
        operation_ids = Mock()
        drawer = Mock(spec=CardDrawer)
        market = Market({}, users=[buyer], packs=[pack], id_factory=operation_ids)

        def snapshot() -> tuple:
            return (
                buyer.balance, buyer.inventory, buyer.free_packs_remaining,
                buyer.packs_opened_today, buyer.last_opening_day,
                market.get_history(), market.get_active_listings(),
            )

        before = snapshot()
        with self.assertRaises(InsufficientFundsError):
            market.open_pack(buyer, pack, drawer, DAY)
        self.assertEqual(snapshot(), before)
        drawer.draw_card.assert_not_called()
        operation_ids.assert_not_called()

    def test_successful_purchase_transfers_card_and_records_sale(self) -> None:
        market, seller, buyer, listing = self.make_listing(buyer_balance=PRICE)
        card = listing.card

        market.buy_card(buyer, listing, DAY)

        self.assertEqual(buyer.balance, 0)
        self.assertEqual(seller.balance, 690)
        self.assertEqual(seller.inventory, [])
        self.assertEqual(buyer.inventory, [card])
        self.assertIs(buyer.inventory[0], card)
        self.assertFalse(listing.active)
        self.assertEqual(market.get_active_listings(), [])
        history = market.get_history()
        self.assertEqual(len(history), 1)
        sale = history[0]
        self.assertIsInstance(sale, CardSale)
        self.assertEqual(sale.buyer_id, buyer.user_id)
        self.assertEqual(sale.seller_id, seller.user_id)
        self.assertEqual(sale.card_id, card.card_id)
        self.assertEqual(sale.price, 199)
        self.assertEqual(sale.commission, 9)
        self.assertEqual(sale.occurred_at, DAY)
        self.assertEqual(seller.balance + buyer.balance + sale.commission, 699)

    def test_pack_costs_and_daily_limit(self) -> None:
        catalog = {
            rarity: [Player(rarity.value, "Jugador", "Club", "forward", None)]
            for rarity in CardRarity
        }
        buyer = User(1, "Comprador", 1000)
        pack = BronzePack()
        rng = Random(42)
        card_ids = iter(UUID(int=n) for n in range(1, 19))
        drawer = CardDrawer(rng, id_factory=card_ids.__next__)
        market = Market(catalog, users=[buyer], packs=[pack])

        for opening, expected_balance in enumerate([1000, 1000, 1000, 800, 600], start=1):
            with self.subTest(opening=opening):
                market.open_pack(buyer, pack, drawer, DAY)
                self.assertEqual(buyer.balance, expected_balance)
                self.assertEqual(buyer.free_packs_remaining, max(0, 3 - opening))
                self.assertEqual(buyer.packs_opened_today, opening)
                self.assertEqual(len(buyer.inventory), 3 * opening)

        self.assertEqual(
            [operation.paid_amount for operation in market.get_history()],
            [0, 0, 0, 200, 200],
        )

        def snapshot() -> tuple:
            return (
                buyer.balance, buyer.inventory, buyer.free_packs_remaining,
                buyer.packs_opened_today, buyer.last_opening_day,
                market.get_history(), rng.getstate(),
            )

        before = snapshot()
        with self.assertRaisesRegex(ValueError, "otra apertura|otro sobre"):
            market.open_pack(buyer, pack, drawer, DAY)
        self.assertEqual(snapshot(), before)

        next_day = date.fromisoformat(DAY) + timedelta(days=1)
        market.open_pack(buyer, pack, drawer, next_day.isoformat())
        self.assertEqual(buyer.balance, 400)
        self.assertEqual(buyer.packs_opened_today, 1)
        self.assertEqual(buyer.free_packs_remaining, 0)
        self.assertEqual(buyer.last_opening_day, next_day)
        self.assertEqual(len(buyer.inventory), 18)
        self.assertEqual(len({card.card_id for card in buyer.inventory}), 18)
        self.assertEqual(market.get_history()[-1].paid_amount, 200)
        self.assertEqual(len(market.get_history()), 6)

    def test_exchange_with_either_card_published_preserves_state(self) -> None:
        for published_user in (1, 2):
            with self.subTest(published_user=published_user):
                first, second = User(1, "Ana"), User(2, "Bruno")
                first_card = Card("a", "Jugador A", PlayerPosition.FORWARD, CardRarity.COMMON)
                second_card = Card("b", "Jugador B", PlayerPosition.DEFENDER, CardRarity.ELITE)
                first.add_card(first_card)
                second.add_card(second_card)
                operation_ids = Mock()
                market = Market({}, users=[first, second], id_factory=operation_ids)
                seller, card = (first, first_card) if published_user == 1 else (second, second_card)
                listing = market.publish_card(seller, card, 100)

                def snapshot() -> tuple:
                    return (
                        first.balance, second.balance, first.inventory, second.inventory,
                        market.get_history(), market.get_active_listings(), listing.active,
                    )

                before = snapshot()
                with self.assertRaisesRegex(ValueError, "cartas publicadas"):
                    market.exchange_cards(first, first_card, second, second_card, DAY)
                self.assertEqual(snapshot(), before)
                operation_ids.assert_not_called()

    def test_pack_opening_with_unregistered_buyer_preserves_state(self) -> None:
        registered = User(1, "Registrado", 500)
        buyer = User(2, "No registrado", 500)
        catalog = {
            rarity: [Player(rarity.value, "Jugador", "Club", "forward", None)]
            for rarity in CardRarity
        }
        pack = BronzePack()
        rng = Random(42)
        card_ids = Mock(side_effect=[UUID(int=n) for n in range(1, 4)])
        operation_ids = Mock(return_value=UUID(int=4))
        drawer = CardDrawer(rng, id_factory=card_ids)
        market = Market(catalog, users=[registered], packs=[pack], id_factory=operation_ids)

        def snapshot() -> tuple:
            return (
                [(u.balance, u.inventory, u.free_packs_remaining,
                  u.packs_opened_today, u.last_opening_day)
                 for u in (registered, buyer)],
                market.get_active_listings(), market.get_history(), rng.getstate(),
            )

        before = snapshot()
        with self.assertRaisesRegex(ValueError, "comprador no está registrado"):
            market.open_pack(buyer, pack, drawer, DAY)

        self.assertEqual(snapshot(), before)
        card_ids.assert_not_called()
        operation_ids.assert_not_called()
        self.assertEqual(market.reconstruct_users()[0].inventory, registered.inventory)

    def test_exchange_transfers_owned_cards_without_changing_balances(self) -> None:
        first, second = User(1, "Ana", 500), User(2, "Bruno", 700)
        first_card = Card("a", "Jugador A", PlayerPosition.FORWARD, CardRarity.COMMON)
        second_card = Card("b", "Jugador B", PlayerPosition.DEFENDER, CardRarity.ELITE)
        first.add_card(first_card)
        second.add_card(second_card)
        market = Market({}, users=[first, second], id_factory=lambda: UUID(int=10))
        # El ID recibido no debe permitir sustituir los datos del ejemplar real.
        reference = Card("a", "Otro nombre", PlayerPosition.GOALKEEPER, CardRarity.RARE)

        market.exchange_cards(first, reference, second, second_card, DAY)

        self.assertEqual(first.inventory, [second_card])
        self.assertEqual(second.inventory, [first_card])
        self.assertIs(second.inventory[0], first_card)
        self.assertEqual((first.balance, second.balance), (500, 700))
        self.assertEqual(market.get_history(), [
            CardExchange(str(UUID(int=10)), DAY, 1, 2, "a", "b"),
        ])

    def test_exchange_with_unowned_card_preserves_state(self) -> None:
        first, second = User(1, "Ana", 500), User(2, "Bruno", 700)
        first_card = Card("a", "Jugador A", PlayerPosition.FORWARD, CardRarity.COMMON)
        second_card = Card("b", "Jugador B", PlayerPosition.DEFENDER, CardRarity.ELITE)
        unowned = Card("c", "Carta ajena", PlayerPosition.MIDFIELDER, CardRarity.RARE)
        first.add_card(first_card)
        second.add_card(second_card)
        market = Market({}, users=[first, second])
        listing = market.publish_card(second, second_card, 100)

        def snapshot() -> tuple:
            return (
                first.balance, second.balance, first.inventory, second.inventory,
                market.get_history(), market.get_active_listings(), listing.active,
            )

        before = snapshot()
        with self.assertRaisesRegex(ValueError, "segunda carta no pertenece"):
            market.exchange_cards(first, first_card, second, unowned, DAY)
        self.assertEqual(snapshot(), before)

    def test_selected_seeds_change_drawn_players_and_rarities(self) -> None:
        catalog = {
            rarity: [
                Player(f"{rarity.value}-1", f"{rarity.value} A", "Club", "forward", None),
                Player(f"{rarity.value}-2", f"{rarity.value} B", "Club", "defender", None),
            ]
            for rarity in CardRarity
        }
        pack = BronzePack()
        results = []
        for seed in (21, 21, 42):
            card_ids = iter(UUID(int=n) for n in range(1, 4))
            drawer = CardDrawer(Random(seed), id_factory=card_ids.__next__)
            cards = pack.open(catalog, drawer)
            self.assertEqual(len(cards), 3)
            results.append([
                (card.full_name, card.position, card.rarity, card.trait)
                for card in cards
            ])

        self.assertEqual(results[0], results[1])
        # Estas dos semillas concretas producen contenidos distintos con este catálogo.
        # No se afirma que cualquier par de semillas deba dar cartas diferentes.
        self.assertNotEqual(results[0], results[2])

    def test_pack_opening_is_reproducible(self) -> None:
        catalog = {
            rarity: [
                Player(f"{rarity.value}-1", f"{rarity.value} A", "Club", "forward", None),
                Player(f"{rarity.value}-2", f"{rarity.value} B", "Club", "defender", None),
            ]
            for rarity in CardRarity
        }

        results = []
        for _ in range(2):
            buyer = User(1, "Comprador", 500)
            pack = BronzePack()
            market = Market(catalog, users=[buyer], packs=[pack], id_factory=lambda: UUID(int=4))
            card_ids = iter(UUID(int=number) for number in range(1, 4))
            drawer = CardDrawer(Random(42), id_factory=card_ids.__next__)

            cards = market.open_pack(buyer, pack, drawer, DAY)

            self.assertEqual(len(cards), 3)
            self.assertEqual({card.card_id for card in cards}, {str(UUID(int=n)) for n in range(1, 4)})
            self.assertEqual(buyer.inventory, cards)
            self.assertEqual(buyer.balance, 500)
            self.assertEqual(buyer.free_packs_remaining, 2)
            history = market.get_history()
            self.assertEqual(history, [PackOpening(str(UUID(int=4)), DAY, 1, "bronze", 0, tuple(cards))])
            results.append((cards, history))

        self.assertEqual(results[0], results[1])

    def make_listing(self, buyer_balance: int) -> tuple[Market, User, User, MarketListing]:
        seller = User(1, "Vendedor", 500)
        buyer = User(2, "Comprador", buyer_balance)
        card = Card("ejemplar-1", "Jugador", PlayerPosition.FORWARD, CardRarity.COMMON)
        seller.add_card(card)
        market = Market({}, users=[seller, buyer])
        return market, seller, buyer, market.publish_card(seller, card, PRICE)

    def assert_rejected_purchase_preserves_state(
        self, market: Market, seller: User, buyer: User, listing: MarketListing, reason: str,
        error_type: type[ValueError] = ValueError,
    ) -> None:
        def snapshot() -> tuple:
            return (
                seller.balance, buyer.balance, seller.inventory, buyer.inventory,
                listing.active, market.get_active_listings(), market.get_history(),
            )

        before = snapshot()
        with self.assertRaisesRegex(error_type, reason):
            market.buy_card(buyer, listing, DAY)
        self.assertEqual(snapshot(), before)

    def test_purchase_with_insufficient_balance_preserves_state(self) -> None:
        market, seller, buyer, listing = self.make_listing(buyer_balance=PRICE - 1)
        self.assert_rejected_purchase_preserves_state(
            market, seller, buyer, listing, "fondos suficientes",
            error_type=InsufficientFundsError,
        )

    def test_second_purchase_of_closed_listing_preserves_state(self) -> None:
        market, seller, buyer, listing = self.make_listing(buyer_balance=2 * PRICE)
        market.buy_card(buyer, listing, DAY)
        self.assertFalse(listing.active)
        self.assertEqual(len(market.get_history()), 1)

        self.assert_rejected_purchase_preserves_state(
            market, seller, buyer, listing, "publicación no está disponible",
        )
