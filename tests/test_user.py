"""Débitos rechazados y sus excepciones de dominio."""

from unittest import TestCase

from models import InsufficientFundsError, User


class UserTests(TestCase):
    def test_debit_with_insufficient_funds_preserves_balance(self) -> None:
        user = User(1, "Usuario", 100)
        with self.assertRaises(InsufficientFundsError):
            user.debit(101)
        self.assertEqual(user.balance, 100)

    def test_invalid_amount_is_not_reported_as_insufficient_funds(self) -> None:
        user = User(1, "Usuario", 100)
        for amount in (0, -1, True, 1.5):
            with self.subTest(amount=amount):
                with self.assertRaises(ValueError) as raised:
                    user.debit(amount)
                self.assertNotIsInstance(raised.exception, InsufficientFundsError)
                self.assertEqual(user.balance, 100)
