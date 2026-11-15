"""Reglas de comisión, redondeo y validación de importes."""

from unittest import TestCase

from utils.calculations import calculate_sale_amounts


class SaleAmountsTests(TestCase):
    def test_commission_rounds_down_and_preserves_total(self) -> None:
        cases = [
            (1, 0, 1),
            (19, 0, 19),
            (20, 1, 19),
            (199, 9, 190),
            (200, 10, 190),
        ]
        for price, expected_commission, expected_net in cases:
            with self.subTest(price=price):
                commission, net = calculate_sale_amounts(price)
                self.assertEqual((commission, net), (expected_commission, expected_net))
                self.assertEqual(commission + net, price)

    def test_invalid_prices_are_rejected(self) -> None:
        for price in (0, -1, 1.5, True, False, "100", None):
            with self.subTest(price=price), self.assertRaises(ValueError):
                calculate_sale_amounts(price)
