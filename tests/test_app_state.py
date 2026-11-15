"""Persistencia del mercado y recorrido de intercambio por consola."""

from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

import main as console
from app_state import load_market, load_users, save_market, save_users
from models import (
    BronzePack, Card, CardDrawer, CardRarity, Market, Player, PlayerPosition, User,
)

DAY = "2026-11-14"


class AppStateTests(TestCase):
    def make_users(self) -> list[User]:
        first, second = User(1, "Ana", 500), User(2, "Bruno", 700)
        first.add_card(Card("a", "Jugador A", PlayerPosition.FORWARD, CardRarity.COMMON))
        second.add_card(Card("b", "Jugador B", PlayerPosition.DEFENDER, CardRarity.ELITE))
        return [first, second]

    def test_round_trip_preserves_all_operation_types_and_active_listing(self) -> None:
        users = self.make_users()
        first, second = users
        catalog = {
            rarity: [Player(rarity.value, "Jugador", "Club", "forward", None)]
            for rarity in CardRarity
        }
        pack = BronzePack()
        market = Market(catalog, users=users, packs=[pack])
        drawn = market.open_pack(first, pack, CardDrawer(Random(42)), DAY)
        sold = market.publish_card(first, drawn[0], 100)
        market.buy_card(second, sold, DAY)
        market.exchange_cards(first, first.inventory[0], second, second.inventory[0], DAY)
        market.publish_card(first, drawn[1], 200)

        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            save_market(users, market, path)
            restored_users = load_users(path)
            restored = load_market(catalog, restored_users, [pack], path)
            self.assertEqual(restored.get_history(), market.get_history())
            self.assertEqual([t.type for t in restored.get_history()], [
                "pack_opening", "card_sale", "card_exchange",
            ])
            for expected, actual in zip(users, restored_users):
                self.assertEqual(actual.inventory, expected.inventory)
                self.assertEqual(actual.balance, expected.balance)
                self.assertEqual(actual.free_packs_remaining, expected.free_packs_remaining)
                self.assertEqual(actual.packs_opened_today, expected.packs_opened_today)
                self.assertEqual(actual.last_opening_day, expected.last_opening_day)

            listings = restored.get_active_listings()
            self.assertEqual(len(listings), 1)
            self.assertIs(listings[0].seller, restored_users[0])
            self.assertIs(listings[0].card, next(
                card for card in restored_users[0].inventory if card.card_id == drawn[1].card_id
            ))
            restored.buy_card(restored_users[1], listings[0], DAY)
            save_market(restored_users, restored, path)
            reloaded_users = load_users(path)
            reloaded = load_market(catalog, reloaded_users, [pack], path)
            self.assertEqual(reloaded.get_active_listings(), [])
            self.assertEqual(len(reloaded.get_history()), 4)

    def test_old_state_without_history_loads(self) -> None:
        users = self.make_users()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            save_users(users, path)
            market = load_market({}, load_users(path), [], path)
            self.assertEqual(market.get_active_listings(), [])
            self.assertEqual(market.get_history(), [])

    def test_invalid_history_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text(json.dumps({"transactions": [{"type": "unknown"}]}))
            with self.assertRaises(ValueError):
                load_market({}, self.make_users(), [], path)

    def test_console_exchange_is_saved_and_restored(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            users = self.make_users()
            save_users(users, path)
            with (
                patch.object(console, "load_catalog", return_value={}),
                patch.object(console, "load_users", side_effect=lambda: load_users(path)),
                patch.object(console, "load_market", side_effect=lambda c, u, p: load_market(c, u, p, path)),
                patch.object(console, "save_market", side_effect=lambda u, m: save_market(u, m, path)),
                patch("builtins.input", side_effect=["1", "8", "1", "1", "1", "s", "0"]),
                redirect_stdout(StringIO()) as output,
            ):
                console.main()
            self.assertIn("Intercambio completado", output.getvalue())
            restored_users = load_users(path)
            market = load_market({}, restored_users, [], path)
            self.assertEqual([c.card_id for c in restored_users[0].inventory], ["b"])
            self.assertEqual([c.card_id for c in restored_users[1].inventory], ["a"])
            self.assertEqual([u.balance for u in restored_users], [500, 700])
            self.assertEqual(len(market.get_history()), 1)
            self.assertEqual(market.get_history()[0].type, "card_exchange")

    def test_cancelled_console_exchange_does_not_modify_state(self) -> None:
        users = self.make_users()
        market = Market({}, users=users)
        before = [u.inventory for u in users]
        with patch("builtins.input", side_effect=["1", "1", "1", "n"]), redirect_stdout(StringIO()):
            self.assertFalse(console.exchange_cards(market, users[0], users))
        self.assertEqual([u.inventory for u in users], before)
        self.assertEqual(market.get_history(), [])

    def test_failed_write_leaves_previous_snapshot_unchanged(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            users = self.make_users()
            market = Market({}, users=users)
            save_market(users, market, path)
            before = path.read_bytes()
            market.exchange_cards(users[0], users[0].inventory[0], users[1], users[1].inventory[0], DAY)
            with patch.object(Path, "replace", side_effect=OSError("fallo de disco")):
                with self.assertRaises(OSError):
                    save_market(users, market, path)
            self.assertEqual(path.read_bytes(), before)
