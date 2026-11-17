"""Consultas históricas independientes del estado actual y del azar."""

from dataclasses import replace
import json
from pathlib import Path
from random import Random
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from history import rebuild_users
from app_state import load_market, load_users, save_market
from models import BronzePack, Card, CardDrawer, CardRarity, Market, Player, PlayerPosition, User

DAY = "2026-11-15"


def snapshot(users: list[User]) -> tuple:
    return tuple(
        (user.user_id, user.user_name, user.balance, tuple(user.inventory),
         user.free_packs_remaining, user.packs_opened_today, user.last_opening_day)
        for user in users
    )


class HistoryTests(TestCase):
    def make_market(self):
        first, second = User(1, "Ana"), User(2, "Bruno")
        first.add_card(Card("a", "Jugador A", PlayerPosition.FORWARD, CardRarity.COMMON))
        second.add_card(Card("b", "Jugador B", PlayerPosition.DEFENDER, CardRarity.ELITE))
        users = [first, second]
        catalog = {
            rarity: [Player(rarity.value, "Jugador", "Club", "forward", None)]
            for rarity in CardRarity
        }
        pack = BronzePack()
        market = Market(catalog, users=users, packs=[pack])
        drawer = CardDrawer(Random(42))
        states = [snapshot(users)]
        drawn = []
        for _ in range(3):
            drawn.extend(market.open_pack(first, pack, drawer, DAY))
            states.append(snapshot(users))
        listing = market.publish_card(first, drawn[0], 100)
        market.buy_card(second, listing, DAY)
        states.append(snapshot(users))
        market.exchange_cards(first, first.inventory[0], second, second.inventory[0], DAY)
        states.append(snapshot(users))
        market.open_pack(first, pack, drawer, DAY)
        states.append(snapshot(users))
        market.open_pack(first, pack, drawer, "2026-11-16")
        states.append(snapshot(users))
        market.publish_card(first, drawn[1], 100)
        return market, users, catalog, pack, states

    def test_every_checkpoint_matches_actual_users_including_five_operations_ago(self) -> None:
        market, users, _, _, states = self.make_market()
        before = snapshot(users)
        history = market.get_history()
        listing = market.get_active_listings()[0]
        with patch.object(Random, "choices", side_effect=AssertionError("No debe sortear")):
            for position, expected in enumerate(states):
                with self.subTest(position=position):
                    self.assertEqual(
                        snapshot(market.reconstruct_users(len(history) - position)), expected,
                    )
            self.assertEqual(snapshot(market.reconstruct_users(5)), states[2])
        self.assertEqual(snapshot(users), before)
        self.assertEqual(market.get_history(), history)
        self.assertTrue(listing.active)
        self.assertEqual(market.get_active_listings(), [listing])

    def test_returned_users_and_base_are_independent_copies(self) -> None:
        market, users, _, _, states = self.make_market()
        result = market.reconstruct_users(5)
        result[0].debit(1)
        result[0].remove_card(result[0].inventory[0])
        base = market.get_history_base()
        base[0].credit(100)
        self.assertEqual(snapshot(market.reconstruct_users(5)), states[2])
        self.assertEqual(snapshot(market.get_history_base()), states[0])
        self.assertEqual(snapshot(users), states[-1])

    def test_historical_query_survives_saving_and_restarting(self) -> None:
        market, users, catalog, pack, states = self.make_market()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            save_market(users, market, path)
            restored_users = load_users(path)
            restored = load_market(catalog, restored_users, [pack], path)
            self.assertEqual(restored.history_start, 0)
            self.assertEqual(snapshot(restored.reconstruct_users(5)), states[2])
            self.assertEqual(snapshot(restored.reconstruct_users()), snapshot(restored_users))
            restored.open_pack(restored_users[0], pack, CardDrawer(Random(7)), "2026-11-16")
            save_market(restored_users, restored, path)
            again_users = load_users(path)
            again = load_market(catalog, again_users, [pack], path)
            self.assertEqual(snapshot(again.reconstruct_users(6)), states[2])
            self.assertEqual(snapshot(again.reconstruct_users()), snapshot(again_users))

    def test_legacy_history_starts_at_known_current_state_without_erasing_operations(self) -> None:
        market, users, catalog, pack, _ = self.make_market()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            save_market(users, market, path)
            data = json.loads(path.read_text())
            del data["history_base"]
            path.write_text(json.dumps(data))
            restored_users = load_users(path)
            restored = load_market(catalog, restored_users, [pack], path)
            self.assertEqual(restored.history_start, 7)
            self.assertEqual(len(restored.get_history()), 7)
            before = snapshot(restored_users)
            self.assertEqual(snapshot(restored.reconstruct_users()), before)
            with self.assertRaises(ValueError):
                restored.reconstruct_users(1)
            restored.open_pack(restored_users[0], pack, CardDrawer(Random(7)), "2026-11-16")
            self.assertEqual(snapshot(restored.reconstruct_users(1)), before)
            save_market(restored_users, restored, path)
            again = load_market(catalog, load_users(path), [pack], path)
            self.assertEqual(again.history_start, 7)
            self.assertEqual(snapshot(again.reconstruct_users(1)), before)

    def test_invalid_query_does_not_modify_any_state(self) -> None:
        market, users, _, _, states = self.make_market()
        for value in [-1, 8, True, 1.5, "5"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                market.reconstruct_users(value)
        self.assertEqual(snapshot(users), states[-1])

    def test_missing_card_and_duplicate_operation_ids_are_rejected_without_changing_base(self) -> None:
        market, _, _, _, states = self.make_market()
        history = market.get_history()
        for bad_sale in [
            replace(history[3], card_id="ausente"),
            replace(history[3], operation_id=history[0].operation_id),
        ]:
            with self.subTest(sale=bad_sale), self.assertRaises(ValueError):
                rebuild_users(market.get_history_base(), history[:3] + [bad_sale], 4)
        self.assertEqual(snapshot(market.get_history_base()), states[0])

    def test_reconstruction_uses_recorded_commission_instead_of_current_rule(self) -> None:
        market, _, _, _, states = self.make_market()
        history = market.get_history()
        sale = replace(history[3], commission=10)
        rebuilt = rebuild_users(market.get_history_base(), history[:3] + [sale], 4)
        self.assertEqual(rebuilt[0].balance, states[3][0][2] + 90)
        self.assertEqual(rebuilt[1].balance, states[3][1][2] - 100)

    def test_invalid_persisted_history_start_is_rejected(self) -> None:
        market, users, catalog, pack, _ = self.make_market()
        with TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            save_market(users, market, path)
            data = json.loads(path.read_text())
            data["history_base"]["after_operations"] = 100
            path.write_text(json.dumps(data))
            with self.assertRaises(ValueError):
                load_market(catalog, load_users(path), [pack], path)
